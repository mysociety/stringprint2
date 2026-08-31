"""
Contract tests for authored publication source loading.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from stringprint2.services.publication_sources import load_publication_source


@dataclass
class SourceContent:
    """
    Record source mutations made by the loader.
    """

    raw: str = "existing"
    saves: int = 0

    def save(self) -> None:
        """
        Record one persistence request.
        """

        self.saves += 1


def test_source_text_is_loaded_and_saved(tmp_path: Path) -> None:
    source = tmp_path / "document.md"
    source.write_text("# Publication\n", encoding="utf-8")
    content = SourceContent()

    result = load_publication_source(content, source)

    assert content.raw == "# Publication\n"
    assert content.saves == 1
    assert result.source == source
    assert result.character_count == 14
    assert result.updated is True


def test_empty_source_preserves_existing_content(tmp_path: Path) -> None:
    source = tmp_path / "document.md"
    source.write_text("", encoding="utf-8")
    content = SourceContent()

    result = load_publication_source(content, source)

    assert content.raw == "existing"
    assert content.saves == 0
    assert result.updated is False
