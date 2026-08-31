"""
Tests for publication archive assembly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from stringprint2.services.publication_archiving import render_publication_archive


class FakePublication:
    """
    Record archive inputs and optionally fail during rendering.
    """

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.render_destination: Path | None = None

    def render(
        self,
        destination: Path,
        refresh_all: bool = False,
    ) -> None:
        self.render_destination = destination
        assert refresh_all
        (destination / "index.html").write_text("Rendered", encoding="utf-8")
        if self.fail:
            raise RuntimeError("render failed")


def write_publication_settings(folder: Path) -> None:
    """
    Write a strict, representative publication configuration.
    """

    (folder / "settings.yaml").write_text(
        """
title: Example
short_title: Example
description: Example publication
byline:
authors:
cite_as: Example
file_source: document.md
publish_date: 2026-01-01
repo_slug: example
commands:
  publish: python publish.py
""".lstrip(),
        encoding="utf-8",
    )


def test_render_publication_archive_includes_media_and_cleans_settings(
    tmp_path: Path,
) -> None:
    write_publication_settings(tmp_path)
    (tmp_path / "hero.png").touch()
    publication = FakePublication()

    result = render_publication_archive(
        publication,
        tmp_path,
        "example",
        refresh=True,
    )

    assert result.location == tmp_path / "example"
    assert [file.destination for file in result.included_files] == [
        Path("hero.png"),
        Path("settings-for-render.json"),
    ]
    assert publication.render_destination is not None
    assert not publication.render_destination.exists()
    assert not (tmp_path / "settings-for-render.json").exists()
    assert (tmp_path / "example.zip").is_file()


def test_render_publication_archive_cleans_settings_after_failure(
    tmp_path: Path,
) -> None:
    write_publication_settings(tmp_path)

    with pytest.raises(RuntimeError, match="render failed"):
        render_publication_archive(
            FakePublication(fail=True),
            tmp_path,
            "example",
            refresh=True,
        )

    assert not (tmp_path / "settings-for-render.json").exists()
