"""Tests for load and archive publication operations."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from stringprint2.services.publication_operations import (
    ArchivePublicationRequest,
    ArchivePublicationResult,
    LoadPublicationRequest,
    LoadPublicationResult,
    run_publication_operation,
    validate_publication_operation,
)


class FakePublication:
    """Provide the publication methods required by shared operation protocols."""

    title = "Example"

    def __init__(self) -> None:
        self.calls = []

    def load_from_yaml(self, folder: Path, refresh_header: bool = False) -> None:
        self.calls.append((folder, refresh_header))

    def import_assets(self, asset_folder: Path, refresh: bool) -> None:
        pass

    def load_from_file(self) -> None:
        pass

    def process(self) -> None:
        pass

    def run_command(self, command: str) -> None:
        pass

    def render(self, destination: Path, refresh_all: bool = False) -> None:
        pass

    def create_ebook(self, destination: Path) -> None:
        pass

    def create_kindle(self, destination: Path) -> None:
        pass


def test_load_operation_uses_shared_configuration_workflow(tmp_path: Path) -> None:
    """Loading is available without duplicating its service orchestration."""
    publication = FakePublication()
    request = LoadPublicationRequest(
        organisation_slug="default",
        publication_slug="example",
        refresh_header=True,
    )

    result = run_publication_operation(
        request,
        publication,
        tmp_path,
        tmp_path / "publish",
    )

    assert result == LoadPublicationResult(title="Example")
    assert publication.calls == [(tmp_path, True)]


def test_archive_operation_returns_zip_artefact(tmp_path: Path, monkeypatch) -> None:
    """Archive requests return the actual ZIP path as a typed artefact."""
    publication = FakePublication()
    captured = []

    def render_archive(document, folder, slug, refresh=False):
        captured.append((document, folder, slug, refresh))
        return SimpleNamespace(location=folder / slug)

    monkeypatch.setattr(
        "stringprint2.services.publication_operations.render_publication_archive",
        render_archive,
    )
    request = validate_publication_operation(
        {
            "operation": "archive",
            "organisation_slug": "default",
            "publication_slug": "example",
            "refresh": True,
        }
    )

    result = run_publication_operation(
        request,
        publication,
        tmp_path,
        tmp_path / "publish",
    )

    assert isinstance(request, ArchivePublicationRequest)
    assert result == ArchivePublicationResult(location=tmp_path / "example.zip")
    assert captured == [(publication, tmp_path, "example", True)]
