"""
Discover publication source directories and classify their load state.
"""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class PublicationCatalogEntry(BaseModel):
    """
    Describe one publication source directory.
    """

    model_config = ConfigDict(frozen=True)

    slug: str
    folder: Path
    loaded: bool


class PublicationCatalog(BaseModel):
    """
    Hold the publications available to the command-line application.
    """

    model_config = ConfigDict(frozen=True)

    entries: tuple[PublicationCatalogEntry, ...]

    @property
    def loaded_slugs(self) -> tuple[str, ...]:
        """
        Return publication slugs already represented in the database.
        """

        return tuple(entry.slug for entry in self.entries if entry.loaded)

    @property
    def unloaded_slugs(self) -> tuple[str, ...]:
        """
        Return publication slugs not yet represented in the database.
        """

        return tuple(entry.slug for entry in self.entries if not entry.loaded)


def discover_publications(
    documents_root: Path,
    loaded_slugs: Collection[str],
) -> PublicationCatalog:
    """
    Find valid, non-template publication directories below a document root.
    """

    loaded = set(loaded_slugs)
    entries = tuple(
        PublicationCatalogEntry(
            slug=folder.name,
            folder=folder,
            loaded=folder.name in loaded,
        )
        for folder in sorted(documents_root.iterdir())
        if folder.is_dir()
        and folder.name != "_template"
        and (folder / "settings.yaml").is_file()
    )
    return PublicationCatalog(entries=entries)
