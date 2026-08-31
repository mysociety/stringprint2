"""Request tests for authenticated publication operation management."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from frontend.models import UserSettings
from publication_management.models import (
    PublicationOperation,
    PublicationOperationState,
)
from publication_management.operation_store import enqueue_publication_operation
from stringprint.models import Article, Organisation
from stringprint2.services.publication_operations import ProcessPublicationRequest


@pytest.fixture
def management_user(org):
    """Create an authenticated user assigned to the fixture organisation."""
    user = User.objects.create_user(username="manager", password="secret")
    UserSettings.objects.create(user=user, org=org)
    return user


@pytest.fixture
def managed_article(org):
    """Create a publication visible to the management user."""
    return Article.objects.create(org=org, slug="managed", title="Managed report")


@pytest.mark.django_db
def test_anonymous_management_requests_redirect_to_login(client) -> None:
    """Neither new nor legacy management pages auto-login an administrator."""
    response = client.get(reverse("publication_management:publication_list"))
    legacy = client.get(reverse("home"))

    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")
    assert legacy.status_code == 302
    assert legacy.url.startswith("/accounts/login/")


@pytest.mark.django_db
def test_user_without_organisation_is_forbidden(client) -> None:
    """Authentication alone does not grant access to the first organisation."""
    user = User.objects.create_user(username="unassigned", password="secret")
    client.force_login(user)

    response = client.get(reverse("publication_management:publication_list"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_publications_are_scoped_to_selected_organisation(
    client,
    management_user,
    managed_article,
) -> None:
    """A user cannot see or address another organisation's publication."""
    other_org = Organisation.objects.create(slug="other", name="Other")
    Article.objects.create(org=other_org, slug="private", title="Private report")
    client.force_login(management_user)

    listing = client.get(reverse("publication_management:publication_list"))
    private = client.get(
        reverse("publication_management:publication_detail", args=("private",))
    )

    assert listing.status_code == 200
    assert b"Managed report" in listing.content
    assert b"Private report" not in listing.content
    assert private.status_code == 404


@pytest.mark.django_db
def test_process_action_enqueues_typed_request(
    client,
    management_user,
    managed_article,
) -> None:
    """A fixed POST action creates durable validated work and redirects to it."""
    client.force_login(management_user)
    url = reverse(
        "publication_management:create_operation",
        args=(managed_article.slug, "process"),
    )

    get_response = client.get(url)
    response = client.post(url, {"preprocess": "on"})

    assert get_response.status_code == 405
    operation = PublicationOperation.objects.get()
    assert response.status_code == 302
    assert response.url == reverse(
        "publication_management:operation_detail",
        args=(operation.pk,),
    )
    assert operation.requested_by == management_user
    assert operation.request_source == "web"
    assert operation.parameters["operation"] == "process"
    assert operation.parameters["preprocess"] is True
    assert operation.parameters["refresh_header"] is False


@pytest.mark.django_db
def test_action_requires_csrf(management_user, managed_article) -> None:
    """Authenticated operation mutations retain Django CSRF enforcement."""
    client = Client(enforce_csrf_checks=True)
    client.force_login(management_user)
    url = reverse(
        "publication_management:create_operation",
        args=(managed_article.slug, "render"),
    )

    response = client.post(url, {"output_format": "web"})

    assert response.status_code == 403
    assert not PublicationOperation.objects.exists()


@pytest.mark.django_db
def test_operation_detail_and_cancel_are_organisation_scoped(
    client,
    management_user,
    org,
) -> None:
    """Operation IDs do not bypass organisation ownership checks."""
    other_org = Organisation.objects.create(slug="other", name="Other")
    operation = enqueue_publication_operation(
        ProcessPublicationRequest(
            organisation_slug=other_org.slug,
            publication_slug="private",
        ),
        other_org,
        request_source="test",
    )
    client.force_login(management_user)

    detail = client.get(
        reverse("publication_management:operation_detail", args=(operation.pk,))
    )
    cancel = client.post(
        reverse("publication_management:cancel_operation", args=(operation.pk,))
    )

    operation.refresh_from_db()
    assert detail.status_code == 404
    assert cancel.status_code == 404
    assert operation.state == PublicationOperationState.PENDING
