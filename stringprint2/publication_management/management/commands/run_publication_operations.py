"""Run the persistent publication operation worker."""

from __future__ import annotations

import os
import signal
import socket
from datetime import timedelta
from threading import Event
from types import FrameType
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from ...operation_store import (
    interrupt_stale_publication_operations,
)
from ...worker import execute_next_publication_operation
from ...worker_health import (
    WorkerHeartbeat,
    register_publication_worker,
    stop_publication_worker,
)


class Command(BaseCommand):
    """Claim and execute durable publication operations."""

    help = "Run the publication operation worker"

    def add_arguments(self, parser: CommandParser) -> None:
        """Configure one-shot and persistent worker behaviour."""
        parser.add_argument(
            "--once",
            action="store_true",
            help="Process at most one operation and exit",
        )
        parser.add_argument(
            "--poll-interval",
            type=float,
            default=1.0,
            help="Seconds to wait when the queue is empty",
        )
        parser.add_argument(
            "--stale-after",
            type=float,
            default=300.0,
            help="Seconds before an abandoned heartbeat is interrupted",
        )

    def handle(self, *args: object, **options: Any) -> None:
        """Recover abandoned work and run until stopped or one-shot completes."""
        worker_id = f"{socket.gethostname()}:{os.getpid()}"
        interrupted = interrupt_stale_publication_operations(
            timedelta(seconds=options["stale_after"])
        )
        if interrupted:
            self.stdout.write(f"Interrupted {interrupted} stale operation(s)")

        shutdown = Event()

        def request_shutdown(
            signal_number: int,
            frame: FrameType | None,
        ) -> None:
            shutdown.set()

        previous_sigterm = signal.signal(signal.SIGTERM, request_shutdown)
        previous_sigint = signal.signal(signal.SIGINT, request_shutdown)
        try:
            worker = register_publication_worker(
                worker_id,
                socket.gethostname(),
                os.getpid(),
            )
            try:
                with WorkerHeartbeat(worker):
                    while not shutdown.is_set():
                        operation = execute_next_publication_operation(worker_id)
                        if options["once"]:
                            return
                        if operation is None:
                            shutdown.wait(options["poll_interval"])
            finally:
                stop_publication_worker(worker)
        finally:
            signal.signal(signal.SIGTERM, previous_sigterm)
            signal.signal(signal.SIGINT, previous_sigint)
