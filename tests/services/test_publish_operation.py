"""Tests for the fixed typed publication workflow."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from stringprint2.services.publication_operations import (
    PublishPublicationRequest,
    PublishPublicationResult,
    run_publication_operation,
)


class FakePublication:
    """Provide the combined workflow and render publication protocols."""

    title = "Example"

    def load_from_yaml(self, folder: Path, refresh_header: bool = False) -> None:
        pass

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


def test_publish_archives_then_runs_only_named_publish_command(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """The browser cannot select an arbitrary configured command name."""
    publication = FakePublication()
    calls = []
    monkeypatch.setattr(
        "stringprint2.services.publication_operations.render_publication_archive",
        lambda document, folder, slug, refresh: (
            calls.append(("archive", slug, refresh))
            or SimpleNamespace(location=folder / slug)
        ),
    )
    monkeypatch.setattr(
        "stringprint2.services.publication_operations.run_publication_command",
        lambda document, folder, command: (
            calls.append(("command", command)) or SimpleNamespace(title=document.title)
        ),
    )
    request = PublishPublicationRequest(
        organisation_slug="default",
        publication_slug="example",
        render_archive=True,
        refresh=True,
    )

    result = run_publication_operation(
        request,
        publication,
        tmp_path,
        tmp_path / "publish",
    )

    assert result == PublishPublicationResult(
        title="Example",
        archive_location=tmp_path / "example.zip",
    )
    assert calls == [("archive", "example", True), ("command", "publish")]
