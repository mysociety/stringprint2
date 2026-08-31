"""
Framework-neutral publication rendering operations.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class PublicationRenderFormat(StrEnum):
    """
    Select one supported publication output format.
    """

    WEB = "web"
    EPUB = "epub"
    KINDLE = "kindle"


class RenderablePublication(Protocol):
    """
    Operations required to render a persisted publication.
    """

    def render(self, destination: Path, refresh_all: bool = False) -> None:
        """
        Render the web publication.
        """

        ...

    def create_ebook(self, destination: Path) -> None:
        """
        Render the EPUB publication.
        """

        ...

    def create_kindle(self, destination: Path) -> None:
        """
        Render the Kindle publication.
        """

        ...


class PublicationRenderResult(BaseModel):
    """
    Describe a completed publication render.
    """

    model_config = ConfigDict(frozen=True)

    destination: Path
    format: PublicationRenderFormat


def render_publication(
    publication: RenderablePublication,
    destination: Path,
    output_format: PublicationRenderFormat,
    *,
    refresh: bool = False,
) -> PublicationRenderResult:
    """
    Render a publication in the selected output format.
    """

    if output_format is PublicationRenderFormat.WEB:
        publication.render(destination, refresh_all=refresh)
    elif output_format is PublicationRenderFormat.EPUB:
        publication.create_ebook(destination)
    else:
        publication.create_kindle(destination)
    return PublicationRenderResult(destination=destination, format=output_format)
