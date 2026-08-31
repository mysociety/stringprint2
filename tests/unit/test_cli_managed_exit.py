"""Tests for clean CLI child shutdown and typed ebook rendering."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from stringprint.models import Article
from stringprint2.__main__ import SPPrompt
from stringprint2.services.publication_operations import RenderPublicationRequest
from stringprint2.services.publication_rendering import PublicationRenderFormat


@pytest.mark.parametrize("command", ["do_quit", "do_exit", "do_EOF"])
def test_shell_exit_paths_stop_owned_services(command, monkeypatch) -> None:
    """Every normal shell exit path stops the worker and preview server."""
    prompt = SPPrompt()
    prompt.running_server = 10
    prompt.running_worker = 11
    stopped = []

    def stop(value):
        stopped.append(value)
        prompt.running_server = None
        prompt.running_worker = None

    monkeypatch.setattr(prompt, "do_stopserver", stop)

    result = getattr(prompt, command)("")

    assert result is True
    assert stopped == [""]


@pytest.mark.parametrize(
    ("command", "expected_format"),
    [
        ("do_renderebook", PublicationRenderFormat.EPUB),
        ("do_renderkindle", PublicationRenderFormat.KINDLE),
    ],
)
def test_ebook_commands_use_locked_typed_render_operation(
    command,
    expected_format,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """All render formats now share the managed foreground operation path."""
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
    monkeypatch.setattr(
        "stringprint2.__main__.run_foreground_publication_operation",
        lambda request, document, source, destination: captured.append(request),
    )

    getattr(prompt, command)("")

    assert len(captured) == 1
    assert isinstance(captured[0], RenderPublicationRequest)
    assert captured[0].output_format is expected_format
