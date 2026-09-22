"""Tests for the publication operation worker command."""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_once_worker_checks_recovery_and_queue_only_once(monkeypatch) -> None:
    """One-shot mode is deterministic for tests and operational diagnosis."""
    calls: list[str] = []
    monkeypatch.setattr(
        "publication_management.management.commands.run_publication_operations.interrupt_stale_publication_operations",
        lambda duration: calls.append(f"recover:{duration.total_seconds()}") or 2,
    )
    monkeypatch.setattr(
        "publication_management.management.commands.run_publication_operations.execute_next_publication_operation",
        lambda worker_id: calls.append(f"execute:{worker_id}"),
    )
    output = StringIO()

    call_command(
        "run_publication_operations",
        once=True,
        stale_after=60,
        stdout=output,
    )

    assert calls[0] == "recover:60.0"
    assert calls[1].startswith("execute:")
    assert "Interrupted 2 stale operation(s)" in output.getvalue()
