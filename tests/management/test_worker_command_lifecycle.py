"""Worker-command liveness lifecycle tests."""

from __future__ import annotations

import pytest
from django.core.management import call_command

from publication_management.models import (
    PublicationWorker,
    PublicationWorkerState,
)


@pytest.mark.django_db
def test_once_command_records_graceful_stopped_state(monkeypatch) -> None:
    """A diagnostic worker does not leave a false active-health record."""
    monkeypatch.setattr(
        "publication_management.management.commands.run_publication_operations.execute_next_publication_operation",
        lambda worker_id: None,
    )

    call_command("run_publication_operations", once=True)

    worker = PublicationWorker.objects.get()
    assert worker.state == PublicationWorkerState.STOPPED
    assert worker.stopped_at is not None
