"""
Load authored publication source into persisted content.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class MutableSourceContent(Protocol):
    """
    Persisted content that accepts authored source text.
    """

    raw: str

    def save(self) -> None:
        """
        Persist the updated source text.
        """

        ...


class PublicationSourceLoadResult(BaseModel):
    """
    Describe authored source loaded into persisted content.
    """

    model_config = ConfigDict(frozen=True)

    source: Path
    character_count: int
    updated: bool


def load_publication_source(
    content: MutableSourceContent,
    source: Path,
) -> PublicationSourceLoadResult:
    """
    Read UTF-8 publication source and persist non-empty content.
    """

    raw = source.read_text(encoding="utf-8")
    if not raw:
        return PublicationSourceLoadResult(
            source=source,
            character_count=0,
            updated=False,
        )
    content.raw = raw
    content.save()
    return PublicationSourceLoadResult(
        source=source,
        character_count=len(raw),
        updated=True,
    )
