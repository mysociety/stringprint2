"""Authenticated web delivery for durable publication operations."""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from frontend.models import UserSettings
from publication_management.cancellation import (
    request_publication_operation_cancellation,
)
from publication_management.logs import read_recent_operation_log
from publication_management.models import PublicationOperation
from publication_management.operation_store import enqueue_publication_operation
from publication_management.worker_health import publication_worker_available
from stringprint.models import Article, Organisation
from stringprint2.services.publication_operations import (
    ArchivePublicationRequest,
    LoadPublicationRequest,
    ProcessPublicationRequest,
    RenderPublicationRequest,
)
from stringprint2.services.publication_rendering import PublicationRenderFormat


def organisation_for_request(request: HttpRequest) -> Organisation:
    """Return the user's selected organisation without creating permissions."""
    membership = (
        UserSettings.objects.select_related("org")
        .filter(user=request.user)
        .order_by("pk")
        .first()
    )
    if membership is None:
        raise PermissionDenied("No organisation is assigned to this user")
    return membership.org


@login_required
def publication_list(request: HttpRequest) -> HttpResponse:
    """List publications the authenticated user is allowed to manage."""
    organisation = organisation_for_request(request)
    publications = Article.objects.filter(org=organisation).order_by("title", "slug")
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
        {"org": organisation, "article": article, "operations": operations},
    )


@login_required
def operation_list(request: HttpRequest) -> HttpResponse:
    """Show operation history scoped to the user's organisation."""
    organisation = organisation_for_request(request)
    operations = PublicationOperation.objects.filter(organisation=organisation)[:100]
    return render(
        request,
        "publication_management/operation_list.html",
        {
            "org": organisation,
            "operations": operations,
            "worker_available": publication_worker_available(timedelta(seconds=30)),
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
    article = get_object_or_404(
        Article,
        org=organisation,
        slug=publication_slug,
    )
    if operation_name == "load":
        operation_request = LoadPublicationRequest(
            organisation_slug=organisation.slug,
            publication_slug=article.slug,
            refresh_header=request.POST.get("refresh_header") == "on",
        )
    elif operation_name == "process":
        operation_request = ProcessPublicationRequest(
            organisation_slug=organisation.slug,
            publication_slug=article.slug,
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
            publication_slug=article.slug,
            output_format=output_format,
            refresh=request.POST.get("refresh") == "on",
        )
    elif operation_name == "archive":
        operation_request = ArchivePublicationRequest(
            organisation_slug=organisation.slug,
            publication_slug=article.slug,
            refresh=request.POST.get("refresh") == "on",
        )
    else:
        return HttpResponseBadRequest("Unsupported publication operation")

    operation = enqueue_publication_operation(
        operation_request,
        organisation,
        article=article,
        requested_by=request.user,
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
    request_publication_operation_cancellation(operation)
    return redirect("publication_management:operation_detail", operation.pk)
