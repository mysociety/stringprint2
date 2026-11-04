"""Authenticated web delivery for durable publication operations."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, cast

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .cancellation import (
    request_publication_operation_cancellation,
)
from .dashboard import (
    build_publication_dashboard,
    publication_source_exists,
)
from .logs import read_recent_operation_log
from .models import (
    PublicationOperation,
    PublicationOperationState,
)
from .operation_store import (
    InvalidOperationTransition,
    enqueue_publication_operation,
)
from .retry import retry_publication_operation
from .worker_health import publication_worker_available
from stringprint2.services.publication_operations import (
    ArchivePublicationRequest,
    LoadPublicationRequest,
    ProcessPublicationRequest,
    PublicationOperationRequest,
    PublishPublicationRequest,
    RenderPublicationRequest,
)
from stringprint2.services.publication_rendering import PublicationRenderFormat

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser
    from django.db.models import Manager
    from stringprint2.frontend.models import UserSettings
    from stringprint2.stringprint.models import Article, Organisation
else:
    from stringprint2.frontend.models import UserSettings
    from stringprint2.stringprint.models import Article, Organisation


def publication_web_operation_allowed(
    article: Article,
    operation_name: str,
) -> bool:
    """Require an authored allow-list entry and matching configured command."""
    if article.org is None:
        return False
    allowed = article.extra_values.get("web_operations", [])
    if not isinstance(allowed, list) or operation_name not in allowed:
        return False
    return operation_name in article.commands or operation_name in article.org.commands


def management_not_found(
    request: HttpRequest,
    unmatched: str,
) -> HttpResponse:
    """Prevent unmatched management URLs falling through to the legacy catch-all."""
    raise Http404(f"Unknown management path: {unmatched}")


def organisation_for_request(request: HttpRequest) -> Organisation:
    """Return the user's selected organisation without creating permissions."""
    user_id = request.user.pk
    if user_id is None:
        raise PermissionDenied("Authentication is required")
    membership_manager = cast("Manager[UserSettings]", getattr(UserSettings, "objects"))
    membership = (
        membership_manager.select_related("org")
        .filter(user_id=user_id)
        .order_by("pk")
        .first()
    )
    if membership is None or membership.org is None:
        raise PermissionDenied("No organisation is assigned to this user")
    return membership.org


@login_required
def publication_list(request: HttpRequest) -> HttpResponse:
    """List publications the authenticated user is allowed to manage."""
    organisation = organisation_for_request(request)
    publications = build_publication_dashboard(organisation)
    return render(
        request,
        "publication_management/publication_list.html",
        {
            "org": organisation,
            "publications": publications,
            "worker_available": publication_worker_available(timedelta(seconds=30)),
        },
    )


@login_required
def publication_detail(
    request: HttpRequest,
    publication_slug: str,
) -> HttpResponse:
    """Show allowed actions and recent work for one publication."""
    organisation = organisation_for_request(request)
    article = get_object_or_404(
        Article,
        org=organisation,
        slug=publication_slug,
    )
    operations = PublicationOperation.objects.filter(
        organisation=organisation,
        publication_slug=publication_slug,
    )[:20]
    return render(
        request,
        "publication_management/publication_detail.html",
        {
            "org": organisation,
            "article": article,
            "operations": operations,
            "publish_allowed": publication_web_operation_allowed(article, "publish"),
        },
    )


@login_required
def operation_list(request: HttpRequest) -> HttpResponse:
    """Show operation history scoped to the user's organisation."""
    organisation = organisation_for_request(request)
    operations = PublicationOperation.objects.filter(organisation=organisation)
    selected_state = request.GET.get("state", "")
    selected_operation = request.GET.get("operation", "")
    publication_slug = request.GET.get("publication", "")
    valid_states = {value for value, label in PublicationOperationState.choices}
    if selected_state in valid_states:
        operations = operations.filter(state=selected_state)
    if selected_operation:
        operations = operations.filter(operation_name=selected_operation)
    if publication_slug:
        operations = operations.filter(publication_slug=publication_slug)
    operations = operations[:100]
    return render(
        request,
        "publication_management/operation_list.html",
        {
            "org": organisation,
            "operations": operations,
            "worker_available": publication_worker_available(timedelta(seconds=30)),
            "state_choices": PublicationOperationState.choices,
            "selected_state": selected_state,
            "selected_operation": selected_operation,
            "selected_publication": publication_slug,
        },
    )


@login_required
def operation_detail(request: HttpRequest, operation_id: int) -> HttpResponse:
    """Show state, result, failure, and recent log output for one operation."""
    organisation = organisation_for_request(request)
    operation = get_object_or_404(
        PublicationOperation,
        pk=operation_id,
        organisation=organisation,
    )
    recent_log = read_recent_operation_log(operation)
    return render(
        request,
        "publication_management/operation_detail.html",
        {"org": organisation, "operation": operation, "recent_log": recent_log},
    )


@login_required
@require_POST
def create_operation(
    request: HttpRequest,
    publication_slug: str,
    operation_name: str,
) -> HttpResponse:
    """Create one fixed typed operation for an authorised publication."""
    organisation = organisation_for_request(request)
    if organisation.slug is None:
        raise ValueError("The organisation must have a slug")
    article_manager = cast("Manager[Article]", getattr(Article, "objects"))
    article = article_manager.filter(
        org=organisation,
        slug=publication_slug,
    ).first()
    if article is None and operation_name != "load":
        raise Http404("Publication is not loaded")
    if article is None and not publication_source_exists(
        organisation, publication_slug
    ):
        raise Http404("Publication source does not exist")
    operation_request: PublicationOperationRequest
    if operation_name == "load":
        if article is None:
            operation_request = ProcessPublicationRequest(
                organisation_slug=organisation.slug,
                publication_slug=publication_slug,
                refresh_header=request.POST.get("refresh_header") == "on",
                preprocess=True,
            )
        else:
            operation_request = LoadPublicationRequest(
                organisation_slug=organisation.slug,
                publication_slug=publication_slug,
                refresh_header=request.POST.get("refresh_header") == "on",
            )
    elif operation_name == "process":
        operation_request = ProcessPublicationRequest(
            organisation_slug=organisation.slug,
            publication_slug=publication_slug,
            refresh_header=request.POST.get("refresh_header") == "on",
            preprocess=request.POST.get("preprocess") == "on",
        )
    elif operation_name == "render":
        try:
            output_format = PublicationRenderFormat(
                request.POST.get("output_format", PublicationRenderFormat.WEB)
            )
        except ValueError:
            return HttpResponseBadRequest("Unsupported render format")
        operation_request = RenderPublicationRequest(
            organisation_slug=organisation.slug,
            publication_slug=publication_slug,
            output_format=output_format,
            refresh=request.POST.get("refresh") == "on",
        )
    elif operation_name == "archive":
        operation_request = ArchivePublicationRequest(
            organisation_slug=organisation.slug,
            publication_slug=publication_slug,
            refresh=request.POST.get("refresh") == "on",
            prepare_hero=request.POST.get("prepare_hero") == "on",
            prepare_thumbnail=request.POST.get("prepare_thumbnail") == "on",
        )
    elif operation_name == "publish":
        assert article is not None
        if not publication_web_operation_allowed(article, "publish"):
            raise PermissionDenied("Web publishing is not enabled for this publication")
        operation_request = PublishPublicationRequest(
            organisation_slug=organisation.slug,
            publication_slug=publication_slug,
            render_archive=True,
            refresh=request.POST.get("refresh") == "on",
            prepare_hero=request.POST.get("prepare_hero") == "on",
            prepare_thumbnail=request.POST.get("prepare_thumbnail") == "on",
        )
    else:
        return HttpResponseBadRequest("Unsupported publication operation")

    operation = enqueue_publication_operation(
        operation_request,
        organisation,
        article=article,
        requested_by=cast("AbstractBaseUser", request.user),
        request_source="web",
    )
    return redirect("publication_management:operation_detail", operation.pk)


@login_required
@require_POST
def cancel_operation(request: HttpRequest, operation_id: int) -> HttpResponse:
    """Request cancellation of one operation in the user's organisation."""
    organisation = organisation_for_request(request)
    operation = get_object_or_404(
        PublicationOperation,
        pk=operation_id,
        organisation=organisation,
    )
    try:
        request_publication_operation_cancellation(operation)
    except InvalidOperationTransition as error:
        return HttpResponseBadRequest(str(error))
    return redirect("publication_management:operation_detail", operation.pk)


@login_required
@require_POST
def retry_operation(request: HttpRequest, operation_id: int) -> HttpResponse:
    """Create a linked pending retry for one authorised terminal operation."""
    organisation = organisation_for_request(request)
    operation = get_object_or_404(
        PublicationOperation,
        pk=operation_id,
        organisation=organisation,
    )
    try:
        retry = retry_publication_operation(
            operation,
            requested_by=cast("AbstractBaseUser", request.user),
            request_source="web-retry",
        )
    except InvalidOperationTransition as error:
        return HttpResponseBadRequest(str(error))
    return redirect("publication_management:operation_detail", retry.pk)
