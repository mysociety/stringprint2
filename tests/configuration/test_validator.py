"""
Tests for whole document-source validation and its command-line interface.
"""

from __future__ import annotations

from pathlib import Path
from shutil import copy

import stringprint_test_env
from stringprint2.configuration.cli import main
from stringprint2.configuration.validator import validate_document_source

FIXTURE_SOURCE = stringprint_test_env.FIXTURES / "doc_source"


def test_fixture_source_is_valid() -> None:
    report = validate_document_source(FIXTURE_SOURCE)

    assert report.is_valid
    assert report.publication_count == 4
    assert report.asset_manifest_count == 3


def test_every_invalid_publication_is_reported(tmp_path: Path) -> None:
    config_dir = tmp_path / "_conf"
    config_dir.mkdir()
    copy(FIXTURE_SOURCE / "_conf" / "settings.yaml", config_dir / "settings.yaml")
    for slug in ("first", "second"):
        document_dir = tmp_path / "_docs" / slug
        document_dir.mkdir(parents=True)
        (document_dir / "settings.yaml").write_text(
            f"title: {slug}\nunknown_key: true\n",
            encoding="utf-8",
        )

    report = validate_document_source(tmp_path)

    assert not report.is_valid
    assert [issue.path.parent.name for issue in report.issues] == ["first", "second"]


def test_cli_returns_success_for_valid_source(capsys) -> None:
    result = main([str(FIXTURE_SOURCE)])

    assert result == 0
    assert "Valid: 4 publications and 3 asset manifests" in capsys.readouterr().out


def test_cli_returns_failure_and_displays_errors(tmp_path: Path, capsys) -> None:
    result = main([str(tmp_path)])

    assert result == 1
    output = capsys.readouterr().out
    assert "Invalid configuration" in output
    assert "_conf/settings.yaml" in output
