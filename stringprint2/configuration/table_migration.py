"""Migrate legacy XLS publication assets to XLSX."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import BaseModel, ConfigDict
from ruamel.yaml import YAML

from stringprint2.table_files import DataTable


class TableMigration(BaseModel):
    """Describe one legacy table asset selected for migration."""

    model_config = ConfigDict(frozen=True)

    manifest: Path
    slug: str
    source: Path
    destination: Path


class TableMigrationReport(BaseModel):
    """Summarize a completed table-asset migration."""

    model_config = ConfigDict(frozen=True)

    source: Path
    manifests_checked: int
    migrations: list[TableMigration]


def find_table_migrations(source: Path) -> tuple[list[Path], list[TableMigration]]:
    """Find declared XLS tables and fail before writing if any file is absent."""
    manifests = sorted((source / "_docs").glob("*/assets/assets.yaml"))
    migrations: list[TableMigration] = []
    missing: list[Path] = []
    yaml = YAML(typ="safe")

    for manifest in manifests:
        with manifest.open(encoding="utf-8") as yaml_file:
            asset_groups = yaml.load(yaml_file) or []
        for asset_group in asset_groups:
            for slug, config in asset_group.items():
                if config.get("content_type") not in {"table", "table-no-header"}:
                    continue
                if config.get("type") != "xls":
                    continue
                legacy_path = manifest.parent / f"{slug}.xls"
                if not legacy_path.exists():
                    missing.append(legacy_path)
                    continue
                migrations.append(
                    TableMigration(
                        manifest=manifest,
                        slug=slug,
                        source=legacy_path,
                        destination=manifest.parent / f"{slug}.xlsx",
                    )
                )

    if missing:
        paths = "\n".join(str(path) for path in missing)
        raise FileNotFoundError(f"Declared XLS assets are missing:\n{paths}")
    return manifests, migrations


def update_manifest(manifest: Path, migrated_slugs: set[str]) -> None:
    """Change migrated asset declarations while preserving YAML presentation."""
    yaml = YAML()
    yaml.preserve_quotes = True
    with manifest.open(encoding="utf-8") as yaml_file:
        asset_groups = yaml.load(yaml_file) or []

    for asset_group in asset_groups:
        for slug, config in asset_group.items():
            if slug in migrated_slugs:
                config["type"] = "xlsx"

    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=manifest.parent,
        prefix=f".{manifest.name}.",
        delete=False,
    ) as yaml_file:
        temporary_path = Path(yaml_file.name)
        yaml.dump(asset_groups, yaml_file)
    temporary_path.replace(manifest)


def migrate_table_assets(
    source: Path,
    *,
    keep_legacy: bool = False,
) -> TableMigrationReport:
    """Convert declared XLS assets to XLSX and update their manifests."""
    resolved_source = source.resolve()
    manifests, migrations = find_table_migrations(resolved_source)

    for migration in migrations:
        DataTable().open(migration.source).save(migration.destination)

    for manifest in manifests:
        migrated_slugs = {
            migration.slug for migration in migrations if migration.manifest == manifest
        }
        if migrated_slugs:
            update_manifest(manifest, migrated_slugs)

    if not keep_legacy:
        for migration in migrations:
            migration.source.unlink()

    return TableMigrationReport(
        source=resolved_source,
        manifests_checked=len(manifests),
        migrations=migrations,
    )
