"""
Tests for publication freshness checks.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from stringprint2.configuration.models import PublicationConfig
from stringprint2.services.publication_freshness import publication_needs_update


def publication_config() -> PublicationConfig:
    """
    Return the smallest valid publication configuration.
    """

    return PublicationConfig(
        title="Example",
        short_title="Example",
        description="Example publication",
        byline=None,
        authors=None,
        cite_as="Example",
        file_source="document.md",
        publish_date=date(2026, 1, 1),
        repo_slug="example",
    )


def test_publication_without_upload_timestamp_is_not_an_update(tmp_path: Path) -> None:
    called = False

    def timestamp_reader(
        repository_root: Path,
        tracked_paths: tuple[Path, ...],
    ) -> datetime | None:
        nonlocal called
        called = True
        return datetime(2026, 1, 2)

    assert not publication_needs_update(
        tmp_path,
        publication_config(),
        timestamp_reader=timestamp_reader,
    )
    assert not called


def test_publication_compares_tracked_inputs_with_upload_time(tmp_path: Path) -> None:
    publication_folder = tmp_path / "_docs" / "example"
    publication_folder.mkdir(parents=True)
    (publication_folder / "upload_time.txt").write_text(
        "2026-01-02T12:00:00",
        encoding="utf-8",
    )
    observed: tuple[Path, tuple[Path, ...]] | None = None

    def timestamp_reader(
        repository_root: Path,
        tracked_paths: tuple[Path, ...],
    ) -> datetime | None:
        nonlocal observed
        observed = (repository_root, tracked_paths)
        return datetime(2026, 1, 3)

    assert publication_needs_update(
        publication_folder,
        publication_config(),
        timestamp_reader=timestamp_reader,
    )
    assert observed == (
        tmp_path,
        (
            Path("_docs/example/settings.yaml"),
            Path("_docs/example/document.md"),
        ),
    )


def test_publication_is_current_when_inputs_are_older(tmp_path: Path) -> None:
    publication_folder = tmp_path / "_docs" / "example"
    publication_folder.mkdir(parents=True)
    (publication_folder / "upload_time.txt").write_text(
        "2026-01-02T12:00:00",
        encoding="utf-8",
    )

    assert not publication_needs_update(
        publication_folder,
        publication_config(),
        timestamp_reader=lambda root, paths: datetime(2026, 1, 1),
    )
