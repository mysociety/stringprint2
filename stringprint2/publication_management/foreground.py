"""Locked foreground delivery of typed publication operations."""

from __future__ import annotations

from pathlib import Path

from publication_management.publication_lock import PublicationLock
from stringprint2.services.publication_operations import (
    ManagedPublication,
    ProgressReporter,
    PublicationOperationRequest,
    PublicationOperationResult,
    run_publication_operation,
)


def run_foreground_publication_operation(
    request: PublicationOperationRequest,
    publication: ManagedPublication,
    source_folder: Path,
    publish_folder: Path,
    progress: ProgressReporter | None = None,
) -> PublicationOperationResult:
    """Execute CLI work under the same publication lock used by workers."""
    with PublicationLock(source_folder, "foreground CLI"):
        return run_publication_operation(
            request,
            publication,
            source_folder,
            publish_folder,
            progress,
        )
