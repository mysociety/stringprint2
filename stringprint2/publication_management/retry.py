"""Explicit retry creation for terminal publication operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from publication_management.models import (
    PublicationOperation,
    PublicationOperationState,
)
from publication_management.operation_store import (
    InvalidOperationTransition,
    enqueue_publication_operation,
)
from stringprint2.services.publication_operations import (
    validate_publication_operation,
)

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser


RETRYABLE_STATES = frozenset(
    {
        PublicationOperationState.FAILED,
        PublicationOperationState.INTERRUPTED,
        PublicationOperationState.CANCELLED,
    }
)


def retry_publication_operation(
    operation: PublicationOperation,
    *,
    requested_by: AbstractBaseUser | None = None,
    request_source: str = "web",
) -> PublicationOperation:
    """Create new pending work linked to a retryable terminal operation."""
    operation.refresh_from_db()
    if operation.state not in RETRYABLE_STATES:
        raise InvalidOperationTransition(
            f"Cannot retry operation while it is {operation.state}"
        )
    request = validate_publication_operation(operation.parameters)
    retry = enqueue_publication_operation(
        request,
        operation.organisation,
        article=operation.article,
        requested_by=requested_by,
        request_source=request_source,
    )
    retry.retry_of = operation
    retry.save(update_fields=("retry_of",))
    return retry
