"""Registration and liveness services for publication workers."""

from __future__ import annotations

from datetime import timedelta
from threading import Event, Thread

from django.db import close_old_connections
from django.utils import timezone

from publication_management.models import (
    PublicationWorker,
    PublicationWorkerState,
)


def register_publication_worker(
    worker_id: str,
    hostname: str,
    process_id: int,
) -> PublicationWorker:
    """Create or replace the liveness record for a starting worker."""
    started_at = timezone.now()
    worker, _ = PublicationWorker.objects.update_or_create(
        worker_id=worker_id,
        defaults={
            "hostname": hostname,
            "process_id": process_id,
            "state": PublicationWorkerState.ACTIVE,
            "started_at": started_at,
            "heartbeat_at": started_at,
            "stopped_at": None,
        },
    )
    return worker


def stop_publication_worker(worker: PublicationWorker) -> None:
    """Record a graceful worker shutdown."""
    stopped_at = timezone.now()
    PublicationWorker.objects.filter(pk=worker.pk).update(
        state=PublicationWorkerState.STOPPED,
        heartbeat_at=stopped_at,
        stopped_at=stopped_at,
    )


def publication_worker_available(stale_after: timedelta) -> bool:
    """Return whether any active worker has a recent heartbeat."""
    return PublicationWorker.objects.filter(
        state=PublicationWorkerState.ACTIVE,
        heartbeat_at__gte=timezone.now() - stale_after,
    ).exists()


class WorkerHeartbeat:
    """Maintain worker liveness while it waits or executes synchronous work."""

    def __init__(self, worker: PublicationWorker, interval: float = 10.0) -> None:
        self.worker = worker
        self.interval = interval
        self.stop_event = Event()
        self.thread: Thread | None = None

    def beat(self) -> bool:
        """Refresh liveness only while the worker remains registered as active."""
        return bool(
            PublicationWorker.objects.filter(
                pk=self.worker.pk,
                state=PublicationWorkerState.ACTIVE,
            ).update(heartbeat_at=timezone.now())
        )

    def run(self) -> None:
        """Publish heartbeats until stopped or no longer active."""
        close_old_connections()
        try:
            while not self.stop_event.wait(self.interval):
                if not self.beat():
                    return
        finally:
            close_old_connections()

    def __enter__(self) -> WorkerHeartbeat:
        """Start the worker heartbeat thread."""
        self.thread = Thread(
            target=self.run,
            name=f"{self.worker.worker_id}-heartbeat",
            daemon=True,
        )
        self.thread.start()
        return self

    def __exit__(self, *args: object) -> None:
        """Stop and join the worker heartbeat thread."""
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=max(self.interval * 2, 1.0))
