"""Tests for cross-process publication locking."""

from __future__ import annotations

from pathlib import Path

import pytest

from publication_management.publication_lock import (
    PublicationLock,
    PublicationLockedError,
)


def test_second_owner_cannot_lock_the_same_publication(tmp_path: Path) -> None:
    """Concurrent foreground and worker mutations are rejected clearly."""
    with PublicationLock(tmp_path, "worker operation 12"):
        with pytest.raises(PublicationLockedError, match="worker operation 12"):
            PublicationLock(tmp_path, "foreground CLI").acquire()


def test_lock_lives_outside_the_publication_folder(tmp_path: Path) -> None:
    """Persistent lock inodes do not clutter authored publication folders."""
    lock = PublicationLock(tmp_path, "worker operation 12")

    with lock:
        assert lock.path.parent.name == "locks"
        assert lock.path.parent.parent.name == ".stringprint"
        assert lock.path.parent != tmp_path

    assert lock.path.exists()
    assert not (tmp_path / ".stringprint-operation.lock").exists()


def test_lock_can_be_reacquired_after_release(tmp_path: Path) -> None:
    """A completed operation leaves the lock available to later work."""
    with PublicationLock(tmp_path, "first"):
        pass

    with PublicationLock(tmp_path, "second") as lock:
        assert lock.handle is not None
