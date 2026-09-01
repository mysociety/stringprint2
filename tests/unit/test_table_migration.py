"""Tests for migrating publication table assets from XLS to XLSX."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from stringprint2.configuration.table_migration import migrate_table_assets
from stringprint2.table_files import DataTable


LEGACY_TABLE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "doc_source"
    / "_docs"
    / "kitchen-sink"
    / "assets"
    / "table-one.xls"
)


def create_source(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create a document source containing one declared legacy table."""
    source = tmp_path / "source"
    assets = source / "_docs" / "publication" / "assets"
    assets.mkdir(parents=True)
    manifest = assets / "assets.yaml"
    manifest.write_text(
        "- table-one:\n"
        "    content_type: table\n"
        "    type: xls\n"
        "    caption: 'Preserve this'\n",
        encoding="utf-8",
    )
    legacy_table = assets / "table-one.xls"
    shutil.copyfile(LEGACY_TABLE, legacy_table)
    return source, manifest, legacy_table


def test_migration_converts_table_and_updates_manifest(tmp_path: Path) -> None:
    """A declared XLS table becomes an equivalent XLSX asset."""
    source, manifest, legacy_table = create_source(tmp_path)
    original = DataTable().open(legacy_table)

    report = migrate_table_assets(source)

    xlsx_table = legacy_table.with_suffix(".xlsx")
    assert len(report.migrations) == 1
    assert not legacy_table.exists()
    assert xlsx_table.exists()
    migrated = DataTable().open(xlsx_table)
    assert migrated.header == original.header
    assert migrated.data == original.data
    config = YAML(typ="safe").load(manifest.read_text(encoding="utf-8"))
    assert config[0]["table-one"]["type"] == "xlsx"
    assert config[0]["table-one"]["caption"] == "Preserve this"


def test_migration_can_retain_legacy_file(tmp_path: Path) -> None:
    """The compatibility option leaves the source XLS file in place."""
    source, _, legacy_table = create_source(tmp_path)

    migrate_table_assets(source, keep_legacy=True)

    assert legacy_table.exists()
    assert legacy_table.with_suffix(".xlsx").exists()


def test_missing_declared_table_prevents_all_writes(tmp_path: Path) -> None:
    """Preflight failure does not partially migrate a repository."""
    source, manifest, legacy_table = create_source(tmp_path)
    legacy_table.unlink()

    with pytest.raises(FileNotFoundError, match="table-one.xls"):
        migrate_table_assets(source)

    assert "type: xls" in manifest.read_text(encoding="utf-8")
    assert not legacy_table.with_suffix(".xlsx").exists()
