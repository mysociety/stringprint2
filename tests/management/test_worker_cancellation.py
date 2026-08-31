"""Integration tests for worker cancellation acknowledgement."""

from __future__ import annotations

from pathlib import Path

import pytest

from publication_management.cancellation import (
    request_publication_operation_cancellation,
)
from publication_management.models import PublicationOperationState
from publication_management.operation_store import enqueue_publication_operation
from publication_management.worker import execute_next_publication_operation
from stringprint2.services.publication_operations import (
    ProcessPublicationRequest,
    PublicationOperationStage,
)


@pytest.mark.django_db
def test_worker_acknowledges_cancellation_at_progress_boundary(
    org,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """An active request stops safely on its next operation stage update."""
    operation = enqueue_publication_operation(
        ProcessPublicationRequest(
            organisation_slug=org.slug,
            publication_slug="minimal-doc",
        ),
        org,
        request_source="test",
    )

    def request_cancellation(request, article, source, destination, progress):
        request_publication_operation_cancellation(operation)
        progress.update(PublicationOperationStage.PROCESSING, "next safe stage")
        raise AssertionError("cancelled operation continued")

    monkeypatch.setattr(
        "publication_management.worker.run_publication_operation",
        request_cancellation,
    )

    cancelled = execute_next_publication_operation("worker", log_root=tmp_path)

    assert cancelled is not None
    assert cancelled.state == PublicationOperationState.CANCELLED
    assert cancelled.finished_at is not None
