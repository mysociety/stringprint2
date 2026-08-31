"""Tests for bounded publication operation retention."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from django.utils import timezone

from publication_management.models import (
    PublicationOperation,
    PublicationOperationState,
)
from publication_management.retention import prune_publication_operations


def terminal_operation(org, finished_at, log_path: Path):
    """Create one old terminal record without executing its workflow."""
    operation = PublicationOperation.objects.create(
        organisation=org,
        publication_slug="minimal-doc",
        operation_name="process",
        parameters={},
        state=PublicationOperationState.FAILED,
        finished_at=finished_at,
        log_path=str(log_path),
        request_source="test",
    )
    return operation


@pytest.mark.django_db
def test_dry_run_reports_without_deleting_rows_or_logs(org, tmp_path: Path) -> None:
    """Operators can inspect retention effects before destructive cleanup."""
    log_root = tmp_path / "logs"
    log_root.mkdir()
    log = log_root / "old.log"
    log.write_text("old")
    operation = terminal_operation(
        org,
        timezone.now() - timedelta(days=100),
        log,
    )

    result = prune_publication_operations(
        timezone.now() - timedelta(days=90),
        log_root,
        dry_run=True,
    )

    assert result.operation_ids == (operation.pk,)
    assert result.log_paths == (log,)
    assert log.exists()
    assert PublicationOperation.objects.filter(pk=operation.pk).exists()


@pytest.mark.django_db
def test_prune_deletes_only_terminal_rows_and_owned_logs(org, tmp_path: Path) -> None:
    """Retention cannot remove active work or files outside its configured root."""
    log_root = tmp_path / "logs"
    log_root.mkdir()
    owned = log_root / "owned.log"
    external = tmp_path / "external.log"
    owned.write_text("owned")
    external.write_text("external")
    old = timezone.now() - timedelta(days=100)
    owned_operation = terminal_operation(org, old, owned)
    external_operation = terminal_operation(org, old, external)
    active = PublicationOperation.objects.create(
        organisation=org,
        publication_slug="active",
        operation_name="process",
        parameters={},
        state=PublicationOperationState.RUNNING,
        heartbeat_at=old,
        request_source="test",
    )

    result = prune_publication_operations(
        timezone.now() - timedelta(days=90),
        log_root,
    )

    assert result.operation_ids == (owned_operation.pk, external_operation.pk)
    assert not owned.exists()
    assert external.exists()
    assert not PublicationOperation.objects.filter(pk=owned_operation.pk).exists()
    assert not PublicationOperation.objects.filter(pk=external_operation.pk).exists()
    assert PublicationOperation.objects.filter(pk=active.pk).exists()
