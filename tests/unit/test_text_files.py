"""Tests for the owned text-file helper."""

from __future__ import annotations

from stringprint2.text_files import TextFile


def test_lines_can_be_replaced_and_removed() -> None:
    """Edits made while iterating are applied to the source text."""
    text = TextFile("first\nsecond\nthird")

    for line in text:
        if line == "first":
            assert line.future == "second"
            line.update("changed")
        if line == "second":
            line.update(None)

    assert text.text == "changed\nthird"


def test_utf8_file_round_trip(tmp_path) -> None:
    """Text is read and written explicitly as UTF-8."""
    path = tmp_path / "publication.md"

    TextFile("café", path).save()
    loaded = TextFile().open(path)

    assert loaded.text == "café"
    assert loaded.filename == path
