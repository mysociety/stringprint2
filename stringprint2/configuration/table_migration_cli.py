"""Command-line interface for migrating table assets to XLSX."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .table_migration import migrate_table_assets


def create_parser() -> argparse.ArgumentParser:
    """Build the table migration command's argument parser."""
    parser = argparse.ArgumentParser(
        prog="stringprint-migrate-tables",
        description="Convert declared XLS publication assets to XLSX.",
    )
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="document-source root containing _docs",
    )
    parser.add_argument(
        "--keep-xls",
        action="store_true",
        help="retain legacy XLS files after successful conversion",
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    """Migrate tables in the selected document-source repository."""
    options = create_parser().parse_args(arguments)
    report = migrate_table_assets(options.source, keep_legacy=options.keep_xls)
    print(
        f"Converted {len(report.migrations)} tables across "
        f"{report.manifests_checked} asset manifests in {report.source}"
    )
    return 0
