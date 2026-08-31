"""Tests for CLI delegation of load and archive operations."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from stringprint.models import Article
from stringprint2.__main__ import SPPrompt
from stringprint2.services.publication_operations import (
    ArchivePublicationRequest,
    ArchivePublicationResult,
    LoadPublicationRequest,
    LoadPublicationResult,
)


def configured_prompt(tmp_path: Path) -> SPPrompt:
    """Build a prompt with one selected publication and no database setup."""
    prompt = SPPrompt()
    prompt.current_org = SimpleNamespace(
        slug="default",
        storage_dir=str(tmp_path),
        publish_dir=str(tmp_path / "publish"),
    )
    prompt.current_doc = "example"
    (tmp_path / "_docs" / "example").mkdir(parents=True)
    return prompt


def test_load_delegates_to_typed_operation(tmp_path, monkeypatch) -> None:
    """The documented load command uses the same contract as queued work."""
    prompt = configured_prompt(tmp_path)
    publication = object()
    captured = []
    monkeypatch.setattr(
        Article.objects,
        "get_or_create",
        lambda **kwargs: (publication, False),
    )

    def run(request, document, source, destination):
        captured.append((request, document, source, destination))
        return LoadPublicationResult(title="Example")

    monkeypatch.setattr(
        "stringprint2.__main__.run_foreground_publication_operation", run
    )

    prompt.do_load("--refresh")

    request, document, source, destination = captured[0]
    assert isinstance(request, LoadPublicationRequest)
    assert request.refresh_header
    assert document is publication
    assert source == tmp_path / "_docs" / "example"
    assert destination == tmp_path / "publish" / "example"


def test_renderzip_delegates_to_archive_operation(tmp_path, monkeypatch) -> None:
    """ZIP rendering remains documented while using the managed operation path."""
    prompt = configured_prompt(tmp_path)
    prompt.running_server = 10
    publication = object()
    monkeypatch.setattr(prompt, "do_hero", lambda value: None)
    monkeypatch.setattr(prompt, "do_pdfpng", lambda value: None)
    monkeypatch.setattr(
        Article.objects,
        "get_or_create",
        lambda **kwargs: (publication, False),
    )
    captured = []

    def run(request, document, source, destination):
        captured.append((request, document, source, destination))
        return ArchivePublicationResult(location=source / "example.zip")

    monkeypatch.setattr(
        "stringprint2.__main__.run_foreground_publication_operation", run
    )

    prompt.do_renderzip("--no-hero --no-thumbnail refresh")

    request, document, source, destination = captured[0]
    assert isinstance(request, ArchivePublicationRequest)
    assert request.refresh
    assert document is publication
    assert source == tmp_path / "_docs" / "example"
    assert destination == tmp_path / "publish" / "example"
