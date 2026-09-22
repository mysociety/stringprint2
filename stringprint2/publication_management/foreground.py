"""Locked foreground delivery of typed publication operations."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from .publication_lock import PublicationLock
from stringprint2.services.publication_operations import (
    ManagedPublication,
    ProgressReporter,
    PublicationOperationRequest,
    PublicationOperationResult,
    run_publication_operation,
)

ActionResult = TypeVar("ActionResult")


def run_locked_publication_action(
    source_folder: Path,
    action: Callable[[], ActionResult],
) -> ActionResult:
    """Run a foreground filesystem mutation under the publication lock."""
    with PublicationLock(source_folder, "foreground CLI"):
        return action()


def run_foreground_publication_operation(
    request: PublicationOperationRequest,
    publication: ManagedPublication,
    source_folder: Path,
    publish_folder: Path,
    progress: ProgressReporter | None = None,
) -> PublicationOperationResult:
    """Execute CLI work under the same publication lock used by workers."""
    return run_locked_publication_action(
        source_folder,
        lambda: run_publication_operation(
            request,
            publication,
            source_folder,
            publish_folder,
            progress,
        ),
    )
