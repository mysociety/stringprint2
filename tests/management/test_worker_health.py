"""Tests for publication worker health registration."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from publication_management.models import PublicationWorkerState
from publication_management.worker_health import (
    WorkerHeartbeat,
    publication_worker_available,
    register_publication_worker,
    stop_publication_worker,
)


@pytest.mark.django_db
def test_active_recent_worker_is_available() -> None:
    """Availability is explicit even when the operation queue is empty."""
    worker = register_publication_worker("host:10", "host", 10)

    assert worker.state == PublicationWorkerState.ACTIVE
    assert publication_worker_available(timedelta(seconds=30))


@pytest.mark.django_db
def test_stale_or_stopped_worker_is_unavailable() -> None:
    """Old process records cannot make the web UI report a healthy consumer."""
    worker = register_publication_worker("host:10", "host", 10)
    type(worker).objects.filter(pk=worker.pk).update(
        heartbeat_at=timezone.now() - timedelta(minutes=5)
    )
    assert not publication_worker_available(timedelta(seconds=30))

    heartbeat = WorkerHeartbeat(worker)
    assert heartbeat.beat()
    assert publication_worker_available(timedelta(seconds=30))
    stop_publication_worker(worker)
    assert not publication_worker_available(timedelta(seconds=30))
