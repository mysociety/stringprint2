"""
Tests for atomic static-publication replacement.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from stringprint2.services import web_rendering
from stringprint2.services.web_rendering import WebRenderResult


def test_successful_render_replaces_the_previous_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "publication"
    destination.mkdir()
    (destination / "old.html").write_text("old", encoding="utf-8")

    def render(
        publication: object, staging: Path, **options: object
    ) -> WebRenderResult:
        staging.mkdir()
        (staging / "index.html").write_text("new", encoding="utf-8")
        return WebRenderResult(
            destination=staging,
            page_count=1,
            redirect_count=0,
            copied_media_count=0,
        )

    monkeypatch.setattr(web_rendering, "render_web_publication_staging", render)

    result = web_rendering.render_web_publication(object(), destination)

    assert result.destination == destination
    assert (destination / "index.html").read_text(encoding="utf-8") == "new"
    assert not (destination / "old.html").exists()


def test_failed_render_preserves_the_previous_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "publication"
    destination.mkdir()
    previous = destination / "index.html"
    previous.write_text("existing", encoding="utf-8")

    def fail(publication: object, staging: Path, **options: object) -> WebRenderResult:
        staging.mkdir()
        (staging / "partial.html").write_text("partial", encoding="utf-8")
        raise RuntimeError("render failed")

    monkeypatch.setattr(web_rendering, "render_web_publication_staging", fail)

    with pytest.raises(RuntimeError, match="render failed"):
        web_rendering.render_web_publication(object(), destination)

    assert previous.read_text(encoding="utf-8") == "existing"
    assert not (destination / "partial.html").exists()
