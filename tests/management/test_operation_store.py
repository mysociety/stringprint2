"""Tests for durable publication operation lifecycle services."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from publication_management.models import (
    PublicationOperation,
    PublicationOperationState,
)
from publication_management.operation_store import (
    InvalidOperationTransition,
    claim_next_publication_operation,
    complete_publication_operation,
    enqueue_publication_operation,
    fail_publication_operation,
    interrupt_stale_publication_operations,
    transition_publication_operation,
    update_publication_operation_progress,
)
from stringprint2.services.publication_operations import (
    ProcessPublicationRequest,
    ProcessPublicationResult,
    PublicationOperationStage,
)


def process_request(organisation_slug: str, publication_slug: str = "one"):
    """Build a representative typed operation request."""
    return ProcessPublicationRequest(
        organisation_slug=organisation_slug,
        publication_slug=publication_slug,
    )


@pytest.mark.django_db
def test_enqueue_validates_organisation_identity(org) -> None:
    """Serialized work cannot silently cross organisation boundaries."""
    request = process_request("different")

    with pytest.raises(ValueError, match="organisation"):
        enqueue_publication_operation(request, org)


@pytest.mark.django_db
def test_claim_owns_the_oldest_pending_operation(org) -> None:
    """A conditional database update gives one worker ownership of one row."""
    first = enqueue_publication_operation(process_request(org.slug, "first"), org)
    enqueue_publication_operation(process_request(org.slug, "second"), org)

    claimed = claim_next_publication_operation("worker-one")

    assert claimed is not None
    assert claimed.pk == first.pk
    assert claimed.state == PublicationOperationState.RUNNING
    assert claimed.worker_id == "worker-one"
    assert claimed.started_at is not None
    assert claimed.heartbeat_at is not None
    assert (
        PublicationOperation.objects.filter(
            state=PublicationOperationState.PENDING
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_progress_and_completion_record_a_typed_result(org) -> None:
    """Active work records stages, heartbeats, completion, and result JSON."""
    queued = enqueue_publication_operation(process_request(org.slug), org)
    operation = claim_next_publication_operation("worker-one")
    assert operation is not None

    update_publication_operation_progress(
        operation,
        PublicationOperationStage.PROCESSING,
        "Loading assets",
    )
    completed = complete_publication_operation(
        operation,
        ProcessPublicationResult(title="Example"),
    )

    assert completed.pk == queued.pk
    assert completed.state == PublicationOperationState.SUCCEEDED
    assert completed.stage == PublicationOperationStage.COMPLETE
    assert completed.progress_detail == "Loading assets"
    assert completed.finished_at is not None
    assert completed.result == {"operation": "process", "title": "Example"}


@pytest.mark.django_db
def test_terminal_operations_reject_further_transitions(org) -> None:
    """Lifecycle methods cannot revive or rewrite completed work."""
    enqueue_publication_operation(process_request(org.slug), org)
    operation = claim_next_publication_operation("worker-one")
    assert operation is not None
    complete_publication_operation(
        operation,
        ProcessPublicationResult(title="Example"),
    )

    with pytest.raises(InvalidOperationTransition, match="succeeded"):
        transition_publication_operation(
            operation,
            PublicationOperationState.RUNNING,
        )


@pytest.mark.django_db
def test_failure_summary_is_bounded(org) -> None:
    """Failures remain diagnosable without creating unbounded database rows."""
    enqueue_publication_operation(process_request(org.slug), org)
    operation = claim_next_publication_operation("worker-one")
    assert operation is not None

    failed = fail_publication_operation(operation, RuntimeError("x" * 5000))

    assert failed.state == PublicationOperationState.FAILED
    assert failed.error_summary.startswith("RuntimeError: ")
    assert len(failed.error_summary) == 4000


@pytest.mark.django_db
def test_stale_running_operations_are_interrupted(org) -> None:
    """Worker recovery changes only active operations with expired heartbeats."""
    enqueue_publication_operation(process_request(org.slug, "stale"), org)
    stale = claim_next_publication_operation("old-worker")
    assert stale is not None
    PublicationOperation.objects.filter(pk=stale.pk).update(
        heartbeat_at=timezone.now() - timedelta(minutes=10)
    )
    current = enqueue_publication_operation(process_request(org.slug, "current"), org)

    count = interrupt_stale_publication_operations(timedelta(minutes=5))

    stale.refresh_from_db()
    current.refresh_from_db()
    assert count == 1
    assert stale.state == PublicationOperationState.INTERRUPTED
    assert stale.finished_at is not None
    assert current.state == PublicationOperationState.PENDING
