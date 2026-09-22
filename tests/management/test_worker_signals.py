"""Tests for graceful publication worker process signals."""

from __future__ import annotations

import signal

import pytest
from django.core.management import call_command

from publication_management.models import (
    PublicationWorker,
    PublicationWorkerState,
)


@pytest.mark.django_db
def test_sigterm_stops_worker_health_record(monkeypatch) -> None:
    """CLI shutdown permits an immediate replacement instead of a stale lease."""
    handlers = {}
    original = object()

    def install_signal(signal_number, handler):
        previous = handlers.get(signal_number, original)
        handlers[signal_number] = handler
        return previous

    monkeypatch.setattr(
        "publication_management.management.commands.run_publication_operations.signal.signal",
        install_signal,
    )

    def request_stop(worker_id):
        handlers[signal.SIGTERM](signal.SIGTERM, None)
        return None

    monkeypatch.setattr(
        "publication_management.management.commands.run_publication_operations.execute_next_publication_operation",
        request_stop,
    )

    call_command("run_publication_operations", poll_interval=0)

    worker = PublicationWorker.objects.get()
    assert worker.state == PublicationWorkerState.STOPPED
    assert worker.stopped_at is not None
    assert handlers[signal.SIGTERM] is original
    assert handlers[signal.SIGINT] is original
