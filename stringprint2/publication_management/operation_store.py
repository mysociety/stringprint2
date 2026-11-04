"""Durable state transitions for publication operations."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from .models import (
    PublicationOperation,
    PublicationOperationState,
)
from stringprint2.services.publication_operations import (
    PublicationOperationRequest,
    PublicationOperationResult,
    PublicationOperationStage,
    validate_publication_operation,
)

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

    from stringprint2.stringprint.models import Article, Organisation


class InvalidOperationTransition(ValueError):
    """Indicate an attempted operation state transition is not permitted."""


VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    PublicationOperationState.PENDING: frozenset(
        {
            PublicationOperationState.RUNNING,
            PublicationOperationState.CANCELLED,
        }
    ),
    PublicationOperationState.RUNNING: frozenset(
        {
            PublicationOperationState.SUCCEEDED,
            PublicationOperationState.FAILED,
            PublicationOperationState.CANCEL_REQUESTED,
            PublicationOperationState.INTERRUPTED,
        }
    ),
    PublicationOperationState.CANCEL_REQUESTED: frozenset(
        {
            PublicationOperationState.CANCELLED,
            PublicationOperationState.FAILED,
            PublicationOperationState.INTERRUPTED,
        }
    ),
    PublicationOperationState.SUCCEEDED: frozenset(),
    PublicationOperationState.FAILED: frozenset(),
    PublicationOperationState.CANCELLED: frozenset(),
    PublicationOperationState.INTERRUPTED: frozenset(),
}


def enqueue_publication_operation(
    request: PublicationOperationRequest,
    organisation: Organisation,
    *,
    article: Article | None = None,
    requested_by: AbstractBaseUser | None = None,
    request_source: str = "web",
) -> PublicationOperation:
    """Validate and persist one operation request in the pending state."""
    if request.organisation_slug != organisation.slug:
        raise ValueError("The request organisation does not match the operation owner")
    if article is not None and article.slug != request.publication_slug:
        raise ValueError("The request publication does not match the selected article")
    parameters = request.model_dump(mode="json")
    validate_publication_operation(parameters)
    return PublicationOperation.objects.create(
        organisation=organisation,
        article=article,
        publication_slug=request.publication_slug,
        operation_name=request.operation,
        parameters=parameters,
        requested_by_id=requested_by.pk if requested_by is not None else None,
        request_source=request_source,
    )


def transition_publication_operation(
    operation: PublicationOperation,
    target: PublicationOperationState,
) -> PublicationOperation:
    """Apply one legal lifecycle transition to a fresh locked record."""
    with transaction.atomic():
        current = PublicationOperation.objects.select_for_update().get(pk=operation.pk)
        allowed = VALID_TRANSITIONS[current.state]
        if target not in allowed:
            raise InvalidOperationTransition(
                f"Cannot transition publication operation from {current.state} to {target}"
            )
        current.state = target
        current.save(update_fields=("state",))
    operation.refresh_from_db()
    return operation


def claim_next_publication_operation(worker_id: str) -> PublicationOperation | None:
    """Atomically claim the oldest pending operation for one worker."""
    while True:
        operation_id = (
            PublicationOperation.objects.filter(state=PublicationOperationState.PENDING)
            .order_by("created_at", "pk")
            .values_list("pk", flat=True)
            .first()
        )
        if operation_id is None:
            return None
        claimed_at = timezone.now()
        claimed = PublicationOperation.objects.filter(
            pk=operation_id,
            state=PublicationOperationState.PENDING,
        ).update(
            state=PublicationOperationState.RUNNING,
            worker_id=worker_id,
            started_at=claimed_at,
            heartbeat_at=claimed_at,
        )
        if claimed:
            return PublicationOperation.objects.get(pk=operation_id)


def update_publication_operation_progress(
    operation: PublicationOperation,
    stage: PublicationOperationStage,
    detail: str = "",
) -> None:
    """Record progress and heartbeat only while an operation is active."""
    updated = PublicationOperation.objects.filter(
        pk=operation.pk,
        state__in=(
            PublicationOperationState.RUNNING,
            PublicationOperationState.CANCEL_REQUESTED,
        ),
    ).update(stage=stage, progress_detail=detail, heartbeat_at=timezone.now())
    if not updated:
        operation.refresh_from_db()
        raise InvalidOperationTransition(
            f"Cannot update progress while operation is {operation.state}"
        )


def complete_publication_operation(
    operation: PublicationOperation,
    result: PublicationOperationResult,
) -> PublicationOperation:
    """Record a successful typed result for a running operation."""
    completed_at = timezone.now()
    updated = PublicationOperation.objects.filter(
        pk=operation.pk,
        state=PublicationOperationState.RUNNING,
    ).update(
        state=PublicationOperationState.SUCCEEDED,
        stage=PublicationOperationStage.COMPLETE,
        heartbeat_at=completed_at,
        finished_at=completed_at,
        result=result.model_dump(mode="json"),
    )
    if not updated:
        operation.refresh_from_db()
        raise InvalidOperationTransition(
            f"Cannot complete operation while it is {operation.state}"
        )
    operation.refresh_from_db()
    return operation


def fail_publication_operation(
    operation: PublicationOperation,
    error: BaseException,
) -> PublicationOperation:
    """Record a bounded failure summary for an active operation."""
    failed_at = timezone.now()
    summary = f"{type(error).__name__}: {error}"[:4000]
    updated = PublicationOperation.objects.filter(
        pk=operation.pk,
        state__in=(
            PublicationOperationState.RUNNING,
            PublicationOperationState.CANCEL_REQUESTED,
        ),
    ).update(
        state=PublicationOperationState.FAILED,
        heartbeat_at=failed_at,
        finished_at=failed_at,
        error_summary=summary,
    )
    if not updated:
        operation.refresh_from_db()
        raise InvalidOperationTransition(
            f"Cannot fail operation while it is {operation.state}"
        )
    operation.refresh_from_db()
    return operation


def interrupt_stale_publication_operations(
    stale_after: timedelta,
) -> int:
    """Mark active operations with expired heartbeats as interrupted."""
    interrupted_at = timezone.now()
    return int(
        PublicationOperation.objects.filter(
            state__in=(
                PublicationOperationState.RUNNING,
                PublicationOperationState.CANCEL_REQUESTED,
            ),
            heartbeat_at__lt=interrupted_at - stale_after,
        ).update(
            state=PublicationOperationState.INTERRUPTED,
            finished_at=interrupted_at,
            error_summary="Worker heartbeat expired",
        )
    )
