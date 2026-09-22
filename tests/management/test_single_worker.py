"""Tests for the default single publication worker lease."""

from __future__ import annotations

import pytest
from django.utils import timezone

from publication_management.models import PublicationWorker
from publication_management.worker_health import (
    WorkerAlreadyRunning,
    register_publication_worker,
)


@pytest.mark.django_db
def test_second_fresh_worker_is_rejected() -> None:
    """Local startup cannot silently create competing publication workers."""
    register_publication_worker("host:10", "host", 10)

    with pytest.raises(WorkerAlreadyRunning, match="host:10"):
        register_publication_worker("host:11", "host", 11)


@pytest.mark.django_db
def test_stale_worker_does_not_block_replacement() -> None:
    """A crashed worker record relinquishes ownership after its heartbeat expires."""
    old = register_publication_worker("host:10", "host", 10)
    PublicationWorker.objects.filter(pk=old.pk).update(
        heartbeat_at=timezone.now() - timezone.timedelta(minutes=1)
    )

    replacement = register_publication_worker("host:11", "host", 11)

    assert replacement.worker_id == "host:11"
