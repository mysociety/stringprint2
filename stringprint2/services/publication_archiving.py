"""
Assemble reproducible publication ZIP archives.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from stringprint2.configuration.loaders import validate_config
from stringprint2.configuration.models import PublicationConfig


class ArchiveFile(BaseModel):
    """
    Describe one source file copied into a publication archive.
    """

    model_config = ConfigDict(frozen=True)

    source: Path
    destination: Path


class ArchivablePublication(Protocol):
    """
    Operations required from a publication archive renderer.
    """

    def render_to_zip(
        self,
        zip_destination: Path,
        extra_files: list[tuple[Path, Path]],
        *,
        refresh_all: bool = False,
    ) -> Path:
        """
        Render a publication and its extra files into a ZIP archive.
        """

        ...


class PublicationArchiveResult(BaseModel):
    """
    Describe the completed publication archive.
    """

    model_config = ConfigDict(frozen=True)

    location: Path
    included_files: tuple[ArchiveFile, ...]


def publication_archive_files(
    publication_folder: Path,
    slug: str,
    settings_path: Path,
) -> tuple[ArchiveFile, ...]:
    """
    Return existing optional media plus the generated render settings.
    """

    candidates = (
        publication_folder / "hero.png",
        publication_folder / f"{slug}-cover.png",
        publication_folder / f"{slug}-thumbnail.png",
        settings_path,
    )
    return tuple(
        ArchiveFile(source=path, destination=Path(path.name))
        for path in candidates
        if path.is_file()
    )


def write_render_settings(
    destination: Path,
    config: PublicationConfig,
) -> None:
    """
    Write authored publication settings without executable commands.
    """

    authored_fields = config.model_fields_set - {"commands"}
    data = config.model_dump(mode="json", include=authored_fields)
    destination.write_text(
        json.dumps(data, indent=4),
        encoding="utf-8",
    )


def render_publication_archive(
    publication: ArchivablePublication,
    publication_folder: Path,
    slug: str,
    *,
    refresh: bool = False,
) -> PublicationArchiveResult:
    """
    Render a ZIP with validated settings and always remove temporary metadata.
    """

    settings_source = publication_folder / "settings.yaml"
    config = validate_config(settings_source, PublicationConfig)
    render_settings = publication_folder / "settings-for-render.json"
    write_render_settings(render_settings, config)
    included_files = publication_archive_files(
        publication_folder,
        slug,
        render_settings,
    )
    try:
        location = publication.render_to_zip(
            publication_folder / slug,
            [
                (archive_file.source, archive_file.destination)
                for archive_file in included_files
            ],
            refresh_all=refresh,
        )
    finally:
        render_settings.unlink(missing_ok=True)
    return PublicationArchiveResult(
        location=location,
        included_files=included_files,
    )
