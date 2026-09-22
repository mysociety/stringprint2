"""Tests for operation history filters and lifecycle actions."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from frontend.models import UserSettings
from publication_management.models import PublicationOperationState
from publication_management.operation_store import (
    claim_next_publication_operation,
    enqueue_publication_operation,
    fail_publication_operation,
)
from stringprint2.services.publication_operations import ProcessPublicationRequest


@pytest.fixture
def operation_user(client, org):
    """Authenticate a user assigned to the fixture organisation."""
    user = User.objects.create_user(username="manager", password="secret")
    UserSettings.objects.create(user=user, org=org)
    client.force_login(user)
    return user


def enqueue_process(org, slug: str):
    """Create one representative pending process operation."""
    return enqueue_publication_operation(
        ProcessPublicationRequest(
            organisation_slug=org.slug,
            publication_slug=slug,
        ),
        org,
        request_source="test",
    )


@pytest.mark.django_db
def test_history_filters_by_state_operation_and_publication(
    client,
    operation_user,
    org,
) -> None:
    """Combined filters narrow only the authorised organisation's history."""
    expected = enqueue_process(org, "expected")
    enqueue_process(org, "other")

    response = client.get(
        reverse("publication_management:operation_list"),
        {"state": "pending", "operation": "process", "publication": "expected"},
    )

    assert response.status_code == 200
    assert (
        f'href="{reverse("publication_management:operation_detail", args=(expected.pk,))}"'.encode()
        in response.content
    )
    assert b"other" not in response.content


@pytest.mark.django_db
def test_failed_operation_can_be_retried_from_web(
    client,
    operation_user,
    org,
) -> None:
    """Retry creates linked pending work and redirects to the new record."""
    original = enqueue_process(org, "minimal-doc")
    running = claim_next_publication_operation("worker")
    assert running is not None
    fail_publication_operation(running, RuntimeError("failed"))

    response = client.post(
        reverse("publication_management:retry_operation", args=(original.pk,))
    )

    retry = original.retries.get()
    assert response.status_code == 302
    assert response.url == reverse(
        "publication_management:operation_detail",
        args=(retry.pk,),
    )
    assert retry.state == PublicationOperationState.PENDING
    assert retry.requested_by == operation_user


@pytest.mark.django_db
def test_pending_retry_and_terminal_cancel_return_bad_request(
    client,
    operation_user,
    org,
) -> None:
    """Crafted lifecycle requests produce safe responses instead of server errors."""
    operation = enqueue_process(org, "minimal-doc")

    retry = client.post(
        reverse("publication_management:retry_operation", args=(operation.pk,))
    )
    from publication_management.cancellation import (
        request_publication_operation_cancellation,
    )

    request_publication_operation_cancellation(operation)
    cancel = client.post(
        reverse("publication_management:cancel_operation", args=(operation.pk,))
    )

    assert retry.status_code == 400
    assert cancel.status_code == 400


@pytest.mark.django_db
def test_active_operation_detail_refreshes_until_terminal(
    client,
    operation_user,
    org,
) -> None:
    """Active logs refresh every five seconds and terminal history stays still."""
    operation = enqueue_process(org, "minimal-doc")
    url = reverse("publication_management:operation_detail", args=(operation.pk,))

    active = client.get(url)
    operation.state = PublicationOperationState.SUCCEEDED
    operation.save(update_fields=("state",))
    terminal = client.get(url)

    assert active.status_code == 200
    assert b'http-equiv="refresh"' in active.content
    assert b'content="5"' in active.content
    assert b"refreshes every five seconds" in active.content
    assert b"card mb-4" in active.content
    assert b'http-equiv="refresh"' not in terminal.content
