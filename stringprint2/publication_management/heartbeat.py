"""Continuous worker heartbeats for long synchronous operation stages."""

from __future__ import annotations

from threading import Event, Thread

from django.db import close_old_connections
from django.utils import timezone

from .models import (
    PublicationOperation,
    PublicationOperationState,
)


class OperationHeartbeat:
    """Update an active operation heartbeat from a small owned thread."""

    def __init__(self, operation: PublicationOperation, interval: float = 10.0) -> None:
        self.operation = operation
        self.interval = interval
        self.stop_event = Event()
        self.thread: Thread | None = None

    def beat(self) -> bool:
        """Refresh the heartbeat if the operation remains active."""
        return bool(
            PublicationOperation.objects.filter(
                pk=self.operation.pk,
                state__in=(
                    PublicationOperationState.RUNNING,
                    PublicationOperationState.CANCEL_REQUESTED,
                ),
            ).update(heartbeat_at=timezone.now())
        )

    def run(self) -> None:
        """Beat at the configured interval until stopped or terminal."""
        close_old_connections()
        try:
            while not self.stop_event.wait(self.interval):
                if not self.beat():
                    return
        finally:
            close_old_connections()

    def __enter__(self) -> OperationHeartbeat:
        """Start the owned heartbeat thread."""
        self.thread = Thread(
            target=self.run,
            name=f"publication-operation-{self.operation.pk}-heartbeat",
            daemon=True,
        )
        self.thread.start()
        return self

    def __exit__(self, *args: object) -> None:
        """Stop and join the owned heartbeat thread."""
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=max(self.interval * 2, 1.0))
