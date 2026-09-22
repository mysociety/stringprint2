"""
Tests for typed asset import planning.
"""

from __future__ import annotations

from pathlib import Path

import stringprint_test_env
from stringprint2.configuration import load_assets_config
from stringprint2.services import build_asset_import_plan

FIXTURE_DOCUMENTS = stringprint_test_env.FIXTURES / "doc_source" / "_docs"


def load_plan(slug: str):
    """
    Build an import plan for one fixture document.
    """
    collection = load_assets_config(FIXTURE_DOCUMENTS / slug / "assets" / "assets.yaml")
    return build_asset_import_plan(collection)


def test_every_authored_asset_becomes_an_item() -> None:
    assert len(load_plan("kitchen-sink").items) == 6


def test_headerless_tables_are_normalized_explicitly() -> None:
    item = next(item for item in load_plan("kitchen-sink").items if item.no_header)

    assert item.content_type == "table"
    assert item.extension == "xlsx"


def test_missing_alt_text_falls_back_to_caption() -> None:
    item = next(
        item
        for item in load_plan("kitchen-sink").items
        if item.slug == "image-three"
    )

    assert item.alt_text == item.caption


def test_explicit_empty_alt_text_is_preserved() -> None:
    item = next(
        item
        for item in load_plan("kitchen-sink").items
        if item.slug == "image-two"
    )

    assert item.alt_text == ""


def test_empty_manifest_produces_an_empty_plan(tmp_path: Path) -> None:
    manifest = tmp_path / "assets.yaml"
    manifest.write_text("[]\n", encoding="utf-8")

    plan = build_asset_import_plan(load_assets_config(manifest))

    assert plan.items == []
