"""
Tests for publication archive assembly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from stringprint2.services.publication_archiving import render_publication_archive


class FakePublication:
    """
    Record archive inputs and optionally fail during rendering.
    """

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.extra_files: list[tuple[Path, Path]] = []

    def render_to_zip(
        self,
        zip_destination: Path,
        extra_files: list[tuple[Path, Path]],
        *,
        refresh_all: bool = False,
    ) -> Path:
        self.extra_files = extra_files
        assert refresh_all
        settings_path = next(
            source
            for source, destination in extra_files
            if destination == Path("settings-for-render.json")
        )
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        assert "commands" not in settings
        assert settings["title"] == "Example"
        if self.fail:
            raise RuntimeError("render failed")
        return zip_destination


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
    assert not (tmp_path / "settings-for-render.json").exists()


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
