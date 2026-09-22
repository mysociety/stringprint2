"""Small text-file helpers used by the publication import pipeline."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any


class EditableLine(str):
    """A string that can replace or remove itself during line iteration."""

    future: EditableLine | None
    replacement: str | None
    changed: bool

    def __new__(cls, value: str) -> EditableLine:
        line = super().__new__(cls, value)
        line.future = None
        line.replacement = value
        line.changed = False
        return line

    def update(self, value: str | None) -> None:
        """Replace this line, or remove it when value is None."""
        self.replacement = value
        self.changed = True


class TextFile:
    """Hold editable UTF-8 text and optionally load or save it from disk."""

    def __init__(
        self,
        text: str = "",
        filename: str | Path | None = None,
    ) -> None:
        self.text = text
        self.filename = Path(filename) if filename else None
        self.assets: list[dict[str, Any]] = []

    def save(self, filename: str | Path | None = None) -> None:
        """Write the current text as UTF-8."""
        target = Path(filename) if filename else self.filename
        if target is None:
            raise ValueError("No filename given")
        target.write_text(self.text, encoding="utf-8")
        self.filename = target

    def open(self, filename: str | Path | None = None) -> TextFile:
        """Load UTF-8 text and return this object for fluent use."""
        target = Path(filename) if filename else self.filename
        if target is None:
            raise ValueError("No filename given")
        self.text = target.read_text(encoding="utf-8")
        self.filename = target
        return self

    def conform_quotes(self) -> None:
        """Replace typographic quotes and en spaces with plain-text forms."""
        self.text = (
            self.text.replace("“", '"')
            .replace("”", '"')
            .replace("’", "'")
            .replace("‘", "'")
            .replace("\u2002", " ")
        )

    def from_list(
        self,
        lines: Sequence[str],
        delimiter: str = "\r\n",
    ) -> TextFile:
        """Replace the text with a joined sequence of lines."""
        self.text = delimiter.join(lines)
        return self

    def lines(self, delimiter: str = "\n") -> Iterator[EditableLine]:
        """Yield editable lines and apply their changes after iteration."""
        lines = [EditableLine(value) for value in self.text.split(delimiter)]
        for index, line in enumerate(lines):
            line.future = lines[index + 1] if index + 1 < len(lines) else None
            yield line
        if any(line.changed for line in lines):
            self.text = delimiter.join(
                line.replacement for line in lines if line.replacement is not None
            )

    __iter__ = lines
