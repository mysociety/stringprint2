"""Cancellation services for durable publication operations."""

from __future__ import annotations

from django.utils import timezone

from .models import (
    PublicationOperation,
    PublicationOperationState,
)
from .operation_store import InvalidOperationTransition


class OperationCancelled(RuntimeError):
    """Stop an operation at a safe cooperative cancellation point."""


def request_publication_operation_cancellation(
    operation: PublicationOperation,
) -> PublicationOperation:
    """Cancel pending work immediately or request cancellation of active work."""
    cancelled_at = timezone.now()
    pending = PublicationOperation.objects.filter(
        pk=operation.pk,
        state=PublicationOperationState.PENDING,
    ).update(
        state=PublicationOperationState.CANCELLED,
        finished_at=cancelled_at,
    )
    if not pending:
        running = PublicationOperation.objects.filter(
            pk=operation.pk,
            state=PublicationOperationState.RUNNING,
        ).update(state=PublicationOperationState.CANCEL_REQUESTED)
        if not running:
            operation.refresh_from_db()
            raise InvalidOperationTransition(
                f"Cannot cancel operation while it is {operation.state}"
            )
    operation.refresh_from_db()
    return operation


def cancellation_requested(operation: PublicationOperation) -> bool:
    """Return whether an active operation should stop at its next safe point."""
    return bool(
        PublicationOperation.objects.filter(
            pk=operation.pk,
            state=PublicationOperationState.CANCEL_REQUESTED,
        ).exists()
    )


def mark_publication_operation_cancelled(
    operation: PublicationOperation,
) -> PublicationOperation:
    """Record acknowledgement of an active cancellation request."""
    cancelled_at = timezone.now()
    updated = PublicationOperation.objects.filter(
        pk=operation.pk,
        state=PublicationOperationState.CANCEL_REQUESTED,
    ).update(
        state=PublicationOperationState.CANCELLED,
        heartbeat_at=cancelled_at,
        finished_at=cancelled_at,
    )
    if not updated:
        operation.refresh_from_db()
        raise InvalidOperationTransition(
            f"Cannot acknowledge cancellation while operation is {operation.state}"
        )
    operation.refresh_from_db()
    return operation
