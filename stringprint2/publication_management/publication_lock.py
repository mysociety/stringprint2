"""Cross-process locks for publication source and output mutation."""

from __future__ import annotations

import fcntl
from pathlib import Path
from types import TracebackType
from typing import IO


class PublicationLockedError(RuntimeError):
    """Indicate another process currently owns a publication lock."""


class PublicationLock:
    """Own a non-blocking advisory lock within a publication source folder."""

    def __init__(self, publication_folder: Path, owner: str) -> None:
        self.path = publication_folder / ".stringprint-operation.lock"
        self.owner = owner
        self.handle: IO[str] | None = None

    def acquire(self) -> None:
        """Acquire the lock or report the owner recorded by its holder."""
        self.handle = self.path.open("a+")
        try:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            self.handle.seek(0)
            owner = self.handle.read().strip() or "another process"
            self.handle.close()
            self.handle = None
            raise PublicationLockedError(f"Publication is locked by {owner}") from error
        self.handle.seek(0)
        self.handle.truncate()
        self.handle.write(self.owner)
        self.handle.flush()

    def release(self) -> None:
        """Release this instance's lock without deleting the shared lock file."""
        if self.handle is None:
            return
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()
        self.handle = None

    def __enter__(self) -> PublicationLock:
        """Acquire the publication lock for a managed block."""
        self.acquire()
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Always release the publication lock after a managed block."""
        self.release()
