"""Tests for local CLI child-process supervision."""

from __future__ import annotations

from pathlib import Path
import signal
from subprocess import TimeoutExpired

import pytest

from stringprint2.services.process_supervisor import (
    LocalProcessSupervisor,
    ManagedProcessSpec,
)


class FakeProcess:
    """Record process lifecycle calls without launching children."""

    next_pid = 100

    def __init__(self, arguments, **options) -> None:
        self.arguments = arguments
        self.options = options
        self.pid = FakeProcess.next_pid
        FakeProcess.next_pid += 1
        self.return_code = None
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.return_code

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True
        self.return_code = -9

    def wait(self, timeout=None):
        if self.terminated:
            self.return_code = -15
        return self.return_code


class StubbornProcess(FakeProcess):
    """Ignore graceful termination until the supervisor escalates."""

    def wait(self, timeout=None):
        if not self.killed:
            raise TimeoutExpired(self.arguments, timeout)
        return self.return_code


def specification(tmp_path: Path, name: str = "worker") -> ManagedProcessSpec:
    """Build one representative child-process specification."""
    return ManagedProcessSpec(
        name=name,
        arguments=("python", "manage.py", name),
        working_directory=tmp_path,
        log_path=tmp_path / "logs" / f"{name}.log",
    )


def test_start_records_live_process_and_log_location(tmp_path, monkeypatch) -> None:
    """Status is based on the child handle rather than a bare remembered PID."""
    monkeypatch.setattr("stringprint2.services.process_supervisor.Popen", FakeProcess)
    supervisor = LocalProcessSupervisor()

    status = supervisor.start(specification(tmp_path))

    assert status.running
    assert status.process_id is not None
    assert status.log_path == tmp_path / "logs" / "worker.log"
    process = supervisor.processes["worker"]
    assert process.arguments == ("python", "manage.py", "worker")
    assert process.options["start_new_session"] is True


def test_duplicate_live_process_is_rejected(tmp_path, monkeypatch) -> None:
    """Repeated startup cannot silently create duplicate workers."""
    monkeypatch.setattr("stringprint2.services.process_supervisor.Popen", FakeProcess)
    supervisor = LocalProcessSupervisor()
    spec = specification(tmp_path)
    supervisor.start(spec)

    with pytest.raises(RuntimeError, match="already running"):
        supervisor.start(spec)


def test_stop_all_terminates_in_reverse_startup_order(tmp_path, monkeypatch) -> None:
    """The preview server stops before the worker that supports its actions."""
    monkeypatch.setattr("stringprint2.services.process_supervisor.Popen", FakeProcess)

    def terminate_group(process_id, signal_number):
        process = next(
            item for item in supervisor.processes.values() if item.pid == process_id
        )
        process.terminated = True

    monkeypatch.setattr(
        "stringprint2.services.process_supervisor.os.killpg", terminate_group
    )
    supervisor = LocalProcessSupervisor()
    supervisor.start(specification(tmp_path, "worker"))
    supervisor.start(specification(tmp_path, "server"))

    statuses = supervisor.stop_all()

    assert [status.name for status in statuses] == ["server", "worker"]
    assert all(not status.running for status in statuses)
    assert supervisor.processes["server"].terminated
    assert supervisor.processes["worker"].terminated


def test_stop_escalates_only_the_owned_process_group(tmp_path, monkeypatch) -> None:
    """A stuck child group receives TERM followed by a bounded KILL."""
    monkeypatch.setattr(
        "stringprint2.services.process_supervisor.Popen", StubbornProcess
    )
    supervisor = LocalProcessSupervisor()
    supervisor.start(specification(tmp_path))
    process = supervisor.processes["worker"]
    signals = []

    def signal_group(process_id, signal_number):
        assert process_id == process.pid
        signals.append(signal_number)
        if signal_number == signal.SIGKILL:
            process.killed = True
            process.return_code = -signal.SIGKILL

    monkeypatch.setattr(
        "stringprint2.services.process_supervisor.os.killpg", signal_group
    )

    status = supervisor.stop("worker", timeout=0.01)

    assert signals == [signal.SIGTERM, signal.SIGKILL]
    assert not status.running
