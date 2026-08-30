"""
Article.create_ebook - the epub build.

mkepub runs in process and needs no external binary; the chapters are rendered
through RequestFactory rather than over HTTP.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.external, pytest.mark.slow]


@pytest.fixture
def epub(tmp_path, kitchen_sink) -> Path:
    destination = tmp_path / "ebook"
    destination.mkdir()
    kitchen_sink.create_ebook(destination)
    return destination / "{0}.epub".format(kitchen_sink.slug)


def test_an_epub_is_written(epub: Path) -> None:
    assert epub.exists()


def test_the_epub_is_a_valid_zip(epub: Path) -> None:
    assert zipfile.is_zipfile(str(epub))


def test_it_carries_the_expected_parts(epub: Path) -> None:
    names = zipfile.ZipFile(str(epub)).namelist()
    assert "mimetype" in names
    assert any(name.endswith(".opf") for name in names)
    assert any("chapter" in name.lower() or name.endswith(".xhtml") for name in names)


def test_chapter_content_is_included(epub: Path) -> None:
    archive = zipfile.ZipFile(str(epub))
    body = "".join(
        archive.read(name).decode("utf-8", "ignore")
        for name in archive.namelist()
        if name.endswith((".xhtml", ".html"))
    )
    assert "An ordinary opening paragraph" in body
