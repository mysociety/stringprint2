"""
Render persisted publications as EPUB files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

import mkepub  # type: ignore[import-untyped]
from django.conf import settings
from django.test.client import RequestFactory
from pydantic import BaseModel, ConfigDict


class EbookPublication(Protocol):
    """
    Publication values and relations required for EPUB rendering.
    """

    authors: str | None
    assets: Any
    book_cover: Any
    slug: str
    title: str

    def content(self) -> Any:
        """
        Return compiled publication content.
        """

        ...


class EbookRenderResult(BaseModel):
    """
    Describe a completed EPUB render.
    """

    model_config = ConfigDict(frozen=True)

    destination: Path
    page_count: int
    image_count: int


def render_epub(
    publication: EbookPublication,
    destination: Path,
    *,
    image_asset_type: int,
    chart_asset_type: int,
) -> EbookRenderResult:
    """
    Render publication chapters and active media into one EPUB file.
    """

    from stringprint2.stringprint.views import EbookChapterView

    authors = publication.authors.split(",") if publication.authors else ""
    book = mkepub.Book(title=publication.title, authors=authors)
    book.set_stylesheet(
        """.asset-long-desc{
                        display: None;
                        }"""
    )

    if publication.book_cover and Path(publication.book_cover.path).exists():
        book.set_cover(Path(publication.book_cover.path).read_bytes())

    page_count = 0
    for section in publication.content().sections:
        anchor = section.anchor()
        arguments = (publication.slug, anchor)
        request = RequestFactory().get(f"{publication.slug}/epub/{anchor}")
        response = EbookChapterView.as_view(decorators=False)(request, *arguments)
        content = response.content.decode("utf-8")
        book.add_page(section.name, content.replace('src="/media/', 'src="images/'))
        page_count += 1

    media_files: list[str] = []
    for asset in publication.assets.filter(active=True):
        if asset.type == image_asset_type:
            media_files.append(asset.get_image_name(1200))
        elif asset.type == chart_asset_type and asset.chart.chart_type != "table_chart":
            media_files.append(asset.image_chart.name)

    for filename in media_files:
        source = Path(settings.MEDIA_ROOT) / filename
        book.add_image(filename, source.read_bytes())

    destination.mkdir(parents=True, exist_ok=True)
    output = destination / f"{publication.slug}.epub"
    output.unlink(missing_ok=True)
    book.save(str(output))
    return EbookRenderResult(
        destination=output,
        page_count=page_count,
        image_count=len(media_files),
    )
