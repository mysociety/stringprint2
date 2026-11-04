"""Tests for CLI supervision of the preview server and operation worker."""

from __future__ import annotations

from pathlib import Path

import pytest

from stringprint2.cli import SPPrompt
from stringprint2.services.process_supervisor import ManagedProcessStatus


class RecordingSupervisor:
    """Record service specifications and lifecycle calls."""

    def __init__(self, fail_server: bool = False) -> None:
        self.fail_server = fail_server
        self.started = []
        self.stopped = []

    def start(self, specification):
        self.started.append(specification)
        if specification.name == "server" and self.fail_server:
            raise RuntimeError("server failed")
        process_id = 101 if specification.name == "worker" else 102
        return ManagedProcessStatus(
            name=specification.name,
            running=True,
            process_id=process_id,
            return_code=None,
            log_path=specification.log_path,
        )

    def stop(self, name, timeout=10.0):
        self.stopped.append(name)

    def stop_all(self, timeout=10.0):
        self.stopped.extend(("server", "worker"))
        return ()


def test_startserver_launches_worker_then_preview_server() -> None:
    """The established CLI command starts the complete local environment."""
    prompt = SPPrompt()
    supervisor = RecordingSupervisor()
    prompt.process_supervisor = supervisor

    message = prompt.do_startserver("noprint")

    assert [spec.name for spec in supervisor.started] == ["worker", "server"]
    worker, server = supervisor.started
    assert worker.arguments[-1] == "run_publication_operations"
    assert server.arguments[-2:] == ("runserver", "0.0.0.0:8000")
    assert worker.log_path == Path(".stringprint/logs/worker.log")
    assert server.log_path == Path(".stringprint/logs/server.log")
    assert prompt.running_worker == 101
    assert prompt.running_server == 102
    assert message == "Started server with pid 102 and worker with pid 101"


def test_stopserver_stops_both_services() -> None:
    """The compatibility command shuts down all children in supervisor order."""
    prompt = SPPrompt()
    supervisor = RecordingSupervisor()
    prompt.process_supervisor = supervisor
    prompt.do_startserver("noprint")

    prompt.do_stopserver("")

    assert supervisor.stopped == ["server", "worker"]
    assert prompt.running_server is None
    assert prompt.running_worker is None


def test_server_start_failure_rolls_back_worker() -> None:
    """A half-started local environment does not leave an unnoticed worker."""
    prompt = SPPrompt()
    supervisor = RecordingSupervisor(fail_server=True)
    prompt.process_supervisor = supervisor

    with pytest.raises(RuntimeError, match="server failed"):
        prompt.do_startserver("noprint")

    assert supervisor.stopped == ["worker"]
    assert prompt.running_server is None
    assert prompt.running_worker is None
