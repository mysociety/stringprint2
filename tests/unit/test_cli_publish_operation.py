"""Tests for CLI delegation of configured publishing."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from stringprint.models import Article
from stringprint2.__main__ import SPPrompt
from stringprint2.services.publication_operations import (
    PublishPublicationRequest,
    PublishPublicationResult,
)


def test_publish_command_uses_fixed_typed_operation(tmp_path, monkeypatch) -> None:
    """The documented CLI command shares the worker's fixed publish contract."""
    prompt = SPPrompt()
    prompt.current_org = SimpleNamespace(
        slug="default",
        storage_dir=str(tmp_path),
        publish_dir=str(tmp_path / "publish"),
    )
    prompt.current_doc = "example"
    (tmp_path / "_docs" / "example").mkdir(parents=True)
    publication = object()
    monkeypatch.setattr(
        Article.objects,
        "get_or_create",
        lambda **kwargs: (publication, False),
    )
    captured = []

    def run(request, document, source, destination):
        captured.append((request, document, source, destination))
        return PublishPublicationResult(title="Example")

    monkeypatch.setattr(
        "stringprint2.__main__.run_foreground_publication_operation", run
    )

    prompt.do_publish("no-render-zip")

    request, document, source, destination = captured[0]
    assert isinstance(request, PublishPublicationRequest)
    assert request.render_archive is False
    assert document is publication
    assert source == tmp_path / "_docs" / "example"
    assert destination == tmp_path / "publish" / "example"
