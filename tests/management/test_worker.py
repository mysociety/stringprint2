"""Tests for publication operation worker execution."""

from __future__ import annotations

from pathlib import Path

import pytest

from publication_management.models import PublicationOperationState
from publication_management.operation_store import enqueue_publication_operation
from publication_management.worker import execute_next_publication_operation
from stringprint2.services.publication_operations import (
    ProcessPublicationRequest,
    ProcessPublicationResult,
)


def queued_process(org, publication_slug: str = "minimal-doc"):
    """Create a valid pending process operation."""
    request = ProcessPublicationRequest(
        organisation_slug=org.slug,
        publication_slug=publication_slug,
    )
    return enqueue_publication_operation(request, org, request_source="test")


@pytest.mark.django_db
def test_worker_executes_and_completes_one_operation(
    org,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """The worker resolves runtime dependencies and persists a typed result."""
    operation = queued_process(org)

    def run_operation(request, article, source, destination, progress):
        print("captured worker output")
        progress.update("processing", "Test stage")
        assert article.slug == "minimal-doc"
        assert source.name == "minimal-doc"
        assert destination.name == "minimal-doc"
        return ProcessPublicationResult(title="Completed")

    monkeypatch.setattr(
        "publication_management.worker.run_publication_operation",
        run_operation,
    )

    completed = execute_next_publication_operation(
        "test-worker",
        log_root=tmp_path,
    )

    assert completed is not None
    assert completed.pk == operation.pk
    assert completed.state == PublicationOperationState.SUCCEEDED
    assert completed.article is not None
    assert completed.result == {"operation": "process", "title": "Completed"}
    assert Path(completed.log_path).read_text() == "captured worker output\n"


@pytest.mark.django_db
def test_worker_records_handler_failures(org, tmp_path: Path, monkeypatch) -> None:
    """An operation exception becomes durable failure state and does not escape."""
    queued_process(org)

    def fail_operation(*args, **kwargs):
        raise RuntimeError("render tool unavailable")

    monkeypatch.setattr(
        "publication_management.worker.run_publication_operation",
        fail_operation,
    )

    failed = execute_next_publication_operation("test-worker", log_root=tmp_path)

    assert failed is not None
    assert failed.state == PublicationOperationState.FAILED
    assert failed.error_summary == "RuntimeError: render tool unavailable"
    assert failed.finished_at is not None


@pytest.mark.django_db
def test_worker_returns_none_when_queue_is_empty(tmp_path: Path) -> None:
    """One-shot and polling callers can distinguish an empty queue."""
    assert execute_next_publication_operation("test-worker", log_root=tmp_path) is None
