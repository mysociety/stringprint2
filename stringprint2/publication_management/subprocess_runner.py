"""Owned subprocess execution for durable publication operations."""

from __future__ import annotations

import os
import signal
import time
from pathlib import Path
from subprocess import DEVNULL, STDOUT, Popen, TimeoutExpired
from typing import TextIO

from django.utils import timezone

from publication_management.cancellation import (
    OperationCancelled,
    cancellation_requested,
)
from publication_management.models import (
    PublicationOperation,
    PublicationOperationState,
)


class OperationSubprocessRunner:
    """Run one command in an owned process group with logs and cancellation."""

    def __init__(
        self,
        operation: PublicationOperation,
        log: TextIO,
        *,
        poll_interval: float = 0.25,
        termination_timeout: float = 10.0,
    ) -> None:
        self.operation = operation
        self.log = log
        self.poll_interval = poll_interval
        self.termination_timeout = termination_timeout

    def __call__(self, arguments: list[str], working_directory: str) -> int:
        """Execute a configured command and return its process exit status."""
        process = Popen(
            arguments,
            cwd=Path(working_directory),
            stdout=self.log,
            stderr=STDOUT,
            stdin=DEVNULL,
            text=True,
            start_new_session=True,
        )
        self.operation.process_id = process.pid
        self.operation.save(update_fields=("process_id",))
        try:
            while True:
                return_code = process.poll()
                if return_code is not None:
                    return return_code
                if cancellation_requested(self.operation):
                    self.terminate(process)
                    raise OperationCancelled("Configured command cancelled")
                PublicationOperation.objects.filter(
                    pk=self.operation.pk,
                    state__in=(
                        PublicationOperationState.RUNNING,
                        PublicationOperationState.CANCEL_REQUESTED,
                    ),
                ).update(heartbeat_at=timezone.now())
                time.sleep(self.poll_interval)
        finally:
            PublicationOperation.objects.filter(pk=self.operation.pk).update(
                process_id=None
            )
            self.operation.process_id = None

    def terminate(self, process: Popen[str]) -> None:
        """Terminate only the process group owned by this operation."""
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=self.termination_timeout)
        except TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=self.termination_timeout)
