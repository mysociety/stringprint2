"""
Tests for publication source discovery.
"""

from __future__ import annotations

from pathlib import Path

from stringprint2.services.publication_catalog import discover_publications


def publication_folder(root: Path, slug: str) -> Path:
    """
    Create a minimally valid publication source folder.
    """

    folder = root / slug
    folder.mkdir()
    (folder / "settings.yaml").touch()
    return folder


def test_discover_publications_sorts_and_classifies_entries(tmp_path: Path) -> None:
    publication_folder(tmp_path, "zulu")
    publication_folder(tmp_path, "alpha")

    catalog = discover_publications(tmp_path, {"zulu"})

    assert tuple(entry.slug for entry in catalog.entries) == ("alpha", "zulu")
    assert catalog.loaded_slugs == ("zulu",)
    assert catalog.unloaded_slugs == ("alpha",)


def test_discover_publications_ignores_templates_and_invalid_folders(
    tmp_path: Path,
) -> None:
    publication_folder(tmp_path, "_template")
    (tmp_path / "missing-settings").mkdir()
    (tmp_path / "settings.yaml").touch()

    catalog = discover_publications(tmp_path, ())

    assert catalog.entries == ()
