"""
Keep the fixture representative of the real corpus.

The key surface below is Appendix A of docs/feature-inventory.md: every
settings.yaml and assets.yaml key used across the 66 production documents in
the parent repository. Without this, the fixture would quietly stop covering
the format as documents gain new keys, and the suite would keep passing while
watching less and less.

The expected surface is committed here rather than read from the parent
repository, because the submodule has to be testable on its own.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

import stringprint_test_env

DOCS = stringprint_test_env.FIXTURES / "doc_source" / "_docs"

SETTINGS_KEYS = {
    "title", "short_title", "description", "byline", "authors", "cite_as",
    "file_source", "publish_date", "sections_over_pages", "display_notes",
    "display_footnotes_at_foot", "repo_slug", "header", "book_cover",
    "copyright", "seed", "subtitle", "pdf", "commands", "google_doc_url",
    "pdf_location", "unsplash_title_image_url", "bottom_iframe", "skip_epub",
    "files",
}

HEADER_KEYS = {
    "location", "size", "alt_text", "source_url", "credit", "description",
    "unsplash_id",
}

ASSET_KEYS = {"content_type", "type", "caption", "alt_text", "longdesc"}

CONTENT_TYPES = {"image", "table", "table-no-header", "html"}


def load(path: Path):
    with open(str(path)) as file_handle:
        return YAML(typ="safe").load(file_handle)


def fixture_settings():
    return [load(path) for path in sorted(DOCS.glob("*/settings.yaml"))]


@pytest.mark.parametrize("key", sorted(SETTINGS_KEYS))
def test_every_production_settings_key_is_exercised(key: str) -> None:
    assert any(key in document for document in fixture_settings()), (
        "no fixture document uses {0!r}".format(key)
    )


@pytest.mark.parametrize("key", sorted(HEADER_KEYS))
def test_every_production_header_key_is_exercised(key: str) -> None:
    headers = [
        document["header"]
        for document in fixture_settings()
        if isinstance(document.get("header"), dict)
    ]
    assert any(key in header for header in headers), (
        "no fixture header uses {0!r}".format(key)
    )


def fixture_assets():
    assets = []
    for path in sorted(DOCS.glob("*/assets/assets.yaml")):
        for entry in load(path) or []:
            assets.extend(entry.values())
    return assets


@pytest.mark.parametrize("key", sorted(ASSET_KEYS))
def test_every_production_asset_key_is_exercised(key: str) -> None:
    assert any(key in asset for asset in fixture_assets()), (
        "no fixture asset uses {0!r}".format(key)
    )


@pytest.mark.parametrize("content_type", sorted(CONTENT_TYPES))
def test_every_content_type_is_exercised(content_type: str) -> None:
    used = {asset["content_type"] for asset in fixture_assets()}
    assert content_type in used


def test_an_asset_omits_alt_text_entirely() -> None:
    """
    The caption fallback only fires when the key is absent, so the fixture
    needs one asset that omits it and one that sets it empty.
    """
    assets = fixture_assets()
    assert any("alt_text" not in asset for asset in assets)
    assert any(asset.get("alt_text") == "" for asset in assets)
