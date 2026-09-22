"""Tests for publication operation cancellation."""

from __future__ import annotations

import pytest

from publication_management.cancellation import (
    cancellation_requested,
    mark_publication_operation_cancelled,
    request_publication_operation_cancellation,
)
from publication_management.models import PublicationOperationState
from publication_management.operation_store import (
    InvalidOperationTransition,
    claim_next_publication_operation,
    enqueue_publication_operation,
)
from stringprint2.services.publication_operations import ProcessPublicationRequest


def enqueue_process(org):
    """Create one representative pending operation."""
    return enqueue_publication_operation(
        ProcessPublicationRequest(
            organisation_slug=org.slug,
            publication_slug="minimal-doc",
        ),
        org,
        request_source="test",
    )


@pytest.mark.django_db
def test_pending_operation_is_cancelled_immediately(org) -> None:
    """Work that has not started never needs worker acknowledgement."""
    operation = enqueue_process(org)

    cancelled = request_publication_operation_cancellation(operation)

    assert cancelled.state == PublicationOperationState.CANCELLED
    assert cancelled.finished_at is not None


@pytest.mark.django_db
def test_running_cancellation_requires_worker_acknowledgement(org) -> None:
    """Active work remains distinguishable until it reaches a safe stop point."""
    enqueue_process(org)
    operation = claim_next_publication_operation("worker")
    assert operation is not None

    requested = request_publication_operation_cancellation(operation)

    assert requested.state == PublicationOperationState.CANCEL_REQUESTED
    assert cancellation_requested(operation)
    cancelled = mark_publication_operation_cancelled(operation)
    assert cancelled.state == PublicationOperationState.CANCELLED
    assert cancelled.finished_at is not None


@pytest.mark.django_db
def test_terminal_operation_rejects_cancellation(org) -> None:
    """Cancellation cannot rewrite an already cancelled terminal record."""
    operation = enqueue_process(org)
    request_publication_operation_cancellation(operation)

    with pytest.raises(InvalidOperationTransition, match="cancelled"):
        request_publication_operation_cancellation(operation)
