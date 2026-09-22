"""Tests for operation-owned configured subprocesses."""

from __future__ import annotations

from io import StringIO

import pytest

from publication_management.cancellation import OperationCancelled
from publication_management.operation_store import (
    claim_next_publication_operation,
    enqueue_publication_operation,
)
from publication_management.subprocess_runner import OperationSubprocessRunner
from stringprint2.services.publication_operations import ProcessPublicationRequest


class FakeProcess:
    """Expose deterministic polling and termination state."""

    def __init__(self, arguments, **options) -> None:
        self.arguments = arguments
        self.options = options
        self.pid = 321
        self.polls = 0
        self.waited = []

    def poll(self):
        self.polls += 1
        return None if self.polls == 1 else 0

    def wait(self, timeout=None):
        self.waited.append(timeout)
        return -15


def running_operation(org):
    """Create and claim one operation for subprocess ownership tests."""
    enqueue_publication_operation(
        ProcessPublicationRequest(
            organisation_slug=org.slug,
            publication_slug="minimal-doc",
        ),
        org,
        request_source="test",
    )
    operation = claim_next_publication_operation("worker")
    assert operation is not None
    return operation


@pytest.mark.django_db
def test_runner_tracks_owned_pid_and_returns_exit_status(org, monkeypatch) -> None:
    """A configured child is logged, heartbeat-polled, and disowned on exit."""
    operation = running_operation(org)
    created = []

    def create_process(arguments, **options):
        process = FakeProcess(arguments, **options)
        created.append(process)
        return process

    monkeypatch.setattr(
        "publication_management.subprocess_runner.Popen",
        create_process,
    )
    monkeypatch.setattr(
        "publication_management.subprocess_runner.time.sleep", lambda _: None
    )
    log = StringIO()

    return_code = OperationSubprocessRunner(operation, log)(
        ["tool", "--option"],
        "/tmp",
    )

    operation.refresh_from_db()
    assert return_code == 0
    assert operation.process_id is None
    assert created[0].options["stdout"] is log
    assert created[0].options["start_new_session"] is True


@pytest.mark.django_db
def test_cancellation_terminates_only_owned_process_group(org, monkeypatch) -> None:
    """Cancellation signals the recorded child group and clears process ownership."""
    operation = running_operation(org)
    process = FakeProcess([], cwd="/tmp")
    signals = []
    monkeypatch.setattr(
        "publication_management.subprocess_runner.Popen",
        lambda *args, **kwargs: process,
    )
    monkeypatch.setattr(
        "publication_management.subprocess_runner.cancellation_requested",
        lambda current: True,
    )
    monkeypatch.setattr(
        "publication_management.subprocess_runner.os.killpg",
        lambda process_id, sent_signal: signals.append((process_id, sent_signal)),
    )

    with pytest.raises(OperationCancelled):
        OperationSubprocessRunner(operation, StringIO())(["tool"], "/tmp")

    operation.refresh_from_db()
    assert operation.process_id is None
    assert len(signals) == 1
    assert signals[0][0] == process.pid
    assert process.waited == [10.0]
