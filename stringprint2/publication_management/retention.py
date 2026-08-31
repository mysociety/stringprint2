"""Bounded retention for terminal publication operation history and logs."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from publication_management.models import (
    PublicationOperation,
    PublicationOperationState,
)


TERMINAL_STATES = (
    PublicationOperationState.SUCCEEDED,
    PublicationOperationState.FAILED,
    PublicationOperationState.CANCELLED,
    PublicationOperationState.INTERRUPTED,
)


class OperationPruneResult(BaseModel):
    """Describe operation rows and owned logs selected for pruning."""

    model_config = ConfigDict(frozen=True)

    operation_ids: tuple[int, ...]
    log_paths: tuple[Path, ...]
    dry_run: bool


def prune_publication_operations(
    cutoff: datetime,
    log_root: Path,
    *,
    dry_run: bool = False,
) -> OperationPruneResult:
    """Remove old terminal records and only logs owned below the log root."""
    operations = list(
        PublicationOperation.objects.filter(
            state__in=TERMINAL_STATES,
            finished_at__lt=cutoff,
        ).order_by("pk")
    )
    resolved_root = log_root.resolve()
    log_paths = []
    for operation in operations:
        if not operation.log_path:
            continue
        path = Path(operation.log_path).resolve()
        if path.is_relative_to(resolved_root):
            log_paths.append(path)
            if not dry_run:
                path.unlink(missing_ok=True)
    operation_ids = tuple(operation.pk for operation in operations)
    if operation_ids and not dry_run:
        PublicationOperation.objects.filter(pk__in=operation_ids).delete()
    return OperationPruneResult(
        operation_ids=operation_ids,
        log_paths=tuple(log_paths),
        dry_run=dry_run,
    )
