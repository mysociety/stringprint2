"""Typed local child-process supervision for the interactive CLI."""

from __future__ import annotations

from pathlib import Path
from subprocess import DEVNULL, Popen, TimeoutExpired
from typing import NamedTuple


class ManagedProcessSpec(NamedTuple):
    """Describe one independently executable local service."""

    name: str
    arguments: tuple[str, ...]
    working_directory: Path
    log_path: Path


class ManagedProcessStatus(NamedTuple):
    """Report the current state of one managed child."""

    name: str
    running: bool
    process_id: int | None
    return_code: int | None
    log_path: Path


class LocalProcessSupervisor:
    """Start, inspect, and stop the CLI's directly owned child processes."""

    def __init__(self) -> None:
        self.processes: dict[str, Popen[bytes]] = {}
        self.specifications: dict[str, ManagedProcessSpec] = {}

    def start(self, specification: ManagedProcessSpec) -> ManagedProcessStatus:
        """Start one child unless a child of the same name remains active."""
        existing = self.processes.get(specification.name)
        if existing is not None and existing.poll() is None:
            raise RuntimeError(f"{specification.name} is already running")
        specification.log_path.parent.mkdir(parents=True, exist_ok=True)
        with specification.log_path.open("ab") as output:
            process = Popen(
                specification.arguments,
                cwd=specification.working_directory,
                stdin=DEVNULL,
                stdout=output,
                stderr=output,
                start_new_session=True,
            )
        self.processes[specification.name] = process
        self.specifications[specification.name] = specification
        return self.status(specification.name)

    def status(self, name: str) -> ManagedProcessStatus:
        """Return live state without trusting a previously recorded PID alone."""
        specification = self.specifications[name]
        process = self.processes.get(name)
        if process is None:
            return ManagedProcessStatus(
                name=name,
                running=False,
                process_id=None,
                return_code=None,
                log_path=specification.log_path,
            )
        return_code = process.poll()
        return ManagedProcessStatus(
            name=name,
            running=return_code is None,
            process_id=process.pid,
            return_code=return_code,
            log_path=specification.log_path,
        )

    def stop(self, name: str, timeout: float = 10.0) -> ManagedProcessStatus:
        """Terminate one child gracefully, then force it after a bounded wait."""
        process = self.processes.get(name)
        if process is None or process.poll() is not None:
            return self.status(name)
        process.terminate()
        try:
            process.wait(timeout=timeout)
        except TimeoutExpired:
            process.kill()
            process.wait(timeout=timeout)
        return self.status(name)

    def stop_all(self, timeout: float = 10.0) -> tuple[ManagedProcessStatus, ...]:
        """Stop managed children in reverse startup order."""
        return tuple(
            self.stop(name, timeout) for name in reversed(tuple(self.specifications))
        )
