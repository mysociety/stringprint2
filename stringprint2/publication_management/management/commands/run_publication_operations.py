"""Run the persistent publication operation worker."""

from __future__ import annotations

import os
import socket
import time
from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from publication_management.operation_store import (
    interrupt_stale_publication_operations,
)
from publication_management.worker import execute_next_publication_operation


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

        while True:
            operation = execute_next_publication_operation(worker_id)
            if options["once"]:
                return
            if operation is None:
                time.sleep(options["poll_interval"])
