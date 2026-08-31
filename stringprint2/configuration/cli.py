"""
Command-line interface for read-only configuration validation.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .validator import ValidationReport, validate_document_source


def create_parser() -> argparse.ArgumentParser:
    """
    Build the validation command's argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="stringprint-validate",
        description="Validate a Stringprint document-source repository.",
    )
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="document-source root containing _conf and _docs",
    )
    return parser


def display_report(report: ValidationReport) -> None:
    """
    Print a concise human-readable validation report.
    """
    if report.is_valid:
        print(
            f"Valid: {report.publication_count} publications and "
            f"{report.asset_manifest_count} asset manifests in {report.source}"
        )
        return

    print(f"Invalid configuration in {report.source}:")
    for issue in report.issues:
        print(f"\n{issue.path}\n{issue.message}")


def main(arguments: Sequence[str] | None = None) -> int:
    """
    Validate the selected source repository and return a shell status code.
    """
    options = create_parser().parse_args(arguments)
    report = validate_document_source(options.source)
    display_report(report)
    return 0 if report.is_valid else 1
