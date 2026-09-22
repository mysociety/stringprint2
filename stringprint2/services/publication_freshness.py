"""
Determine whether authored publication inputs changed after publication.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from stringprint2.configuration.models import PublicationConfig

GitTimestampReader = Callable[[Path, tuple[Path, ...]], datetime | None]


def read_last_git_change(
    repository_root: Path,
    tracked_paths: tuple[Path, ...],
) -> datetime | None:
    """
    Return the most recent commit time for specific repository-relative paths.
    """

    result = subprocess.run(
        [
            "git",
            "log",
            "-1",
            "--format=%ct",
            "--",
            *(str(path) for path in tracked_paths),
        ],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    timestamp = result.stdout.strip()
    if not timestamp:
        return None
    return datetime.fromtimestamp(float(timestamp))


def publication_needs_update(
    publication_folder: Path,
    config: PublicationConfig,
    *,
    timestamp_reader: GitTimestampReader = read_last_git_change,
) -> bool:
    """
    Return whether source or settings changed after the last publication.
    """

    upload_time_path = publication_folder / "upload_time.txt"
    if not upload_time_path.is_file():
        return False

    upload_time = datetime.fromisoformat(
        upload_time_path.read_text(encoding="utf-8").strip()
    )
    repository_root = publication_folder.parent.parent
    settings_path = publication_folder / "settings.yaml"
    source_path = publication_folder / config.file_source
    last_change = timestamp_reader(
        repository_root,
        (
            settings_path.relative_to(repository_root),
            source_path.relative_to(repository_root),
        ),
    )
    return last_change is not None and last_change > upload_time
