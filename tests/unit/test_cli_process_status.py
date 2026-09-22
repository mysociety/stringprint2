"""Tests for independent CLI service status reporting."""

from __future__ import annotations

from pathlib import Path

from stringprint2.__main__ import SPPrompt
from stringprint2.services.process_supervisor import ManagedProcessStatus


class CapturingPanel:
    """Capture status panel lines without rendering terminal markup."""

    latest = None

    def __init__(self, *args, **kwargs) -> None:
        self.items = []
        CapturingPanel.latest = self

    def print(self, item: str) -> None:
        self.items.append(item)

    def display(self) -> None:
        pass


class StatusSupervisor:
    """Return different authoritative states for each child."""

    def status(self, name: str) -> ManagedProcessStatus:
        return ManagedProcessStatus(
            name=name,
            running=name == "server",
            process_id=10 if name == "server" else 11,
            return_code=None if name == "server" else 2,
            log_path=Path(f".stringprint/logs/{name}.log"),
        )


def test_status_reports_children_independently(monkeypatch) -> None:
    """A failed worker is visible without treating the preview server as failed."""
    monkeypatch.setattr("stringprint2.__main__.PanelPrint", CapturingPanel)
    prompt = SPPrompt()
    prompt.process_supervisor = StatusSupervisor()
    prompt.running_server = 10
    prompt.running_worker = 11

    prompt.print_status()

    assert CapturingPanel.latest is not None
    assert CapturingPanel.latest.items == [
        "Preview server: [green]running[/green] (pid 10, log .stringprint/logs/server.log)",
        "Operation worker: [red]stopped[/red] (exit 2, log .stringprint/logs/worker.log)",
    ]
    assert prompt.running_server == 10
    assert prompt.running_worker is None
