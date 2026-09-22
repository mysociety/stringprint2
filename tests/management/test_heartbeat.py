"""Tests for long-running publication operation heartbeats."""

from __future__ import annotations

import pytest

from publication_management.cancellation import (
    request_publication_operation_cancellation,
)
from publication_management.heartbeat import OperationHeartbeat
from publication_management.operation_store import (
    claim_next_publication_operation,
    enqueue_publication_operation,
)
from stringprint2.services.publication_operations import ProcessPublicationRequest


@pytest.mark.django_db
def test_heartbeat_refreshes_running_and_cancelling_operations(org) -> None:
    """Long stages remain owned while running and awaiting a safe cancellation."""
    enqueue_publication_operation(
        ProcessPublicationRequest(
            organisation_slug=org.slug,
            publication_slug="minimal-doc",
        ),
        org,
        request_source="test",
    )
    operation = claim_next_publication_operation("worker")
    assert operation is not None
    original = operation.heartbeat_at
    heartbeat = OperationHeartbeat(operation)

    assert heartbeat.beat()
    operation.refresh_from_db()
    assert operation.heartbeat_at is not None
    assert original is not None
    assert operation.heartbeat_at >= original

    request_publication_operation_cancellation(operation)
    assert heartbeat.beat()
