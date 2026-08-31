"""Tests for foreground CLI publication locking."""

from __future__ import annotations

from pathlib import Path

import pytest

from publication_management.foreground import (
    run_foreground_publication_operation,
    run_locked_publication_action,
)
from publication_management.publication_lock import (
    PublicationLock,
    PublicationLockedError,
)
from stringprint2.services.publication_operations import LoadPublicationRequest


class FakePublication:
    """Fail if execution reaches a locked publication workflow."""

    title = "Example"

    def load_from_yaml(self, folder: Path, refresh_header: bool = False) -> None:
        raise AssertionError("locked foreground operation executed")


def test_foreground_operation_rejects_worker_owned_publication(tmp_path: Path) -> None:
    """Direct CLI work cannot race a queued mutation of the same source tree."""
    request = LoadPublicationRequest(
        organisation_slug="default",
        publication_slug="example",
    )

    with PublicationLock(tmp_path, "worker operation 12"):
        with pytest.raises(PublicationLockedError, match="worker operation 12"):
            run_foreground_publication_operation(
                request,
                FakePublication(),
                tmp_path,
                tmp_path / "publish",
            )


def test_direct_foreground_action_rejects_worker_owned_publication(
    tmp_path: Path,
) -> None:
    """CLI-only file conversion and configured commands share worker exclusion."""
    executed = False

    def action() -> None:
        nonlocal executed
        executed = True

    with PublicationLock(tmp_path, "worker operation 18"):
        with pytest.raises(PublicationLockedError, match="worker operation 18"):
            run_locked_publication_action(tmp_path, action)

    assert not executed
