"""
Tests for stale-publication CLI orchestration.
"""

from __future__ import annotations

from pathlib import Path

from stringprint2.cli import SPPrompt


def test_publish_updated_runs_the_complete_pipeline_only_for_stale_documents(
    monkeypatch,
) -> None:
    prompt = object.__new__(SPPrompt)
    selected: list[tuple[str, bool]] = []
    processed: list[str] = []
    rendered: list[str] = []
    published: list[str] = []
    current = {"slug": ""}

    monkeypatch.setattr(
        prompt,
        "get_valid_doc_folders",
        lambda: [Path("current"), Path("stale")],
    )

    def select(slug: str, silent: bool = False) -> None:
        current["slug"] = slug
        selected.append((slug, silent))

    monkeypatch.setattr(prompt, "do_setdoc", select)
    monkeypatch.setattr(
        prompt,
        "do_check_for_update",
        lambda value: current["slug"] == "stale",
    )
    monkeypatch.setattr(prompt, "do_process", processed.append)
    monkeypatch.setattr(prompt, "do_renderzip", rendered.append)
    monkeypatch.setattr(prompt, "do_publish", published.append)

    SPPrompt.do_publish_updated(prompt, "")

    assert selected == [("current", True), ("stale", True)]
    assert processed == ["refresh"]
    assert rendered == ["refresh"]
    assert published == ["no-render-zip"]
