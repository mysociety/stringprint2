"""Execution services for the persistent publication operation worker."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import TYPE_CHECKING, cast

from django.conf import settings

from .cancellation import (
    OperationCancelled,
    cancellation_requested,
    mark_publication_operation_cancelled,
)
from .heartbeat import OperationHeartbeat
from .models import PublicationOperation
from .operation_store import (
    claim_next_publication_operation,
    complete_publication_operation,
    fail_publication_operation,
    update_publication_operation_progress,
)
from .publication_lock import PublicationLock
from .subprocess_runner import OperationSubprocessRunner
from stringprint2.services.configured_commands import command_runner_context
from stringprint2.services.publication_operations import (
    ProgressReporter,
    ManagedPublication,
    PublicationOperationStage,
    run_publication_operation,
    validate_publication_operation,
)

if TYPE_CHECKING:
    from django.db.models import Manager

    from stringprint2.stringprint.models import Article
else:
    from stringprint2.stringprint.models import Article


class DatabaseProgressReporter(ProgressReporter):
    """Persist operation stages and heartbeats from the shared runner."""

    def __init__(self, operation: PublicationOperation) -> None:
        self.operation = operation

    def update(self, stage: PublicationOperationStage, detail: str = "") -> None:
        """Store a progress update for the active operation."""
        if cancellation_requested(self.operation):
            raise OperationCancelled("Cancellation requested")
        update_publication_operation_progress(self.operation, stage, detail)


def operation_log_path(operation: PublicationOperation, log_root: Path | None) -> Path:
    """Return a stable, non-public log location for an operation."""
    root = log_root or Path(settings.MEDIA_ROOT) / "operation_logs"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"operation-{operation.pk}.log"


def execute_publication_operation(
    operation: PublicationOperation,
    *,
    log_root: Path | None = None,
) -> PublicationOperation:
    """Execute one claimed operation and persist its terminal outcome."""
    request = validate_publication_operation(operation.parameters)
    organisation = operation.organisation
    article_manager = cast("Manager[Article]", getattr(Article, "objects"))
    article, _ = article_manager.get_or_create(
        org=organisation,
        slug=request.publication_slug,
    )
    publication = cast("ManagedPublication", article)
    source_folder = Path(
        organisation.storage_dir,
        "_docs",
        request.publication_slug,
    )
    publish_folder = Path(organisation.publish_dir, request.publication_slug)
    log_path = operation_log_path(operation, log_root)
    operation.log_path = str(log_path)
    operation.article = article
    operation.save(update_fields=("log_path", "article"))
    progress = DatabaseProgressReporter(operation)

    try:
        with (
            PublicationLock(source_folder, f"operation {operation.pk}"),
            log_path.open("a", encoding="utf-8") as log,
            redirect_stdout(log),
            redirect_stderr(log),
            OperationHeartbeat(operation),
            command_runner_context(OperationSubprocessRunner(operation, log)),
        ):
            result = run_publication_operation(
                request,
                publication,
                source_folder,
                publish_folder,
                progress,
            )
    except OperationCancelled:
        return mark_publication_operation_cancelled(operation)
    except Exception as error:
        return fail_publication_operation(operation, error)
    return complete_publication_operation(operation, result)


def execute_next_publication_operation(
    worker_id: str,
    *,
    log_root: Path | None = None,
) -> PublicationOperation | None:
    """Claim and execute the next pending operation, if one exists."""
    operation = claim_next_publication_operation(worker_id)
    if operation is None:
        return None
    return execute_publication_operation(operation, log_root=log_root)
