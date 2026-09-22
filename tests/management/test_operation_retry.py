"""Tests for explicit durable operation retries."""

from __future__ import annotations

import pytest

from publication_management.models import PublicationOperationState
from publication_management.operation_store import (
    InvalidOperationTransition,
    claim_next_publication_operation,
    enqueue_publication_operation,
    fail_publication_operation,
)
from publication_management.retry import retry_publication_operation
from stringprint2.services.publication_operations import ProcessPublicationRequest


@pytest.mark.django_db
def test_failed_operation_retry_creates_linked_pending_work(org) -> None:
    """Retry preserves immutable failure history and copies validated parameters."""
    original = enqueue_publication_operation(
        ProcessPublicationRequest(
            organisation_slug=org.slug,
            publication_slug="minimal-doc",
            preprocess=False,
        ),
        org,
        request_source="test",
    )
    running = claim_next_publication_operation("worker")
    assert running is not None
    fail_publication_operation(running, RuntimeError("failed"))

    retry = retry_publication_operation(original, request_source="test-retry")

    original.refresh_from_db()
    assert original.state == PublicationOperationState.FAILED
    assert retry.state == PublicationOperationState.PENDING
    assert retry.retry_of == original
    assert retry.parameters == original.parameters
    assert retry.request_source == "test-retry"


@pytest.mark.django_db
def test_nonterminal_operation_cannot_be_retried(org) -> None:
    """Pending or active work cannot be duplicated through the retry service."""
    operation = enqueue_publication_operation(
        ProcessPublicationRequest(
            organisation_slug=org.slug,
            publication_slug="minimal-doc",
        ),
        org,
        request_source="test",
    )

    with pytest.raises(InvalidOperationTransition, match="pending"):
        retry_publication_operation(operation)
