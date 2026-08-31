"""PDF and image operations used by document publication commands."""

from __future__ import annotations

from pathlib import Path

import pymupdf
from PIL import Image

type PathValue = str | Path


def merge_pdfs(
    front: PathValue,
    contents: PathValue,
    output: PathValue,
    start_page: int = 1,
) -> None:
    """Combine the first front-cover page with content pages from start_page."""
    with (
        pymupdf.open() as result,  # type: ignore[no-untyped-call]
        pymupdf.open(front) as front_document,  # type: ignore[no-untyped-call]
        pymupdf.open(contents) as contents_document,  # type: ignore[no-untyped-call]
    ):
        result.insert_pdf(front_document, from_page=0, to_page=0)
        result.insert_pdf(contents_document, from_page=start_page)
        result.save(output)


def pdf_page_to_png(source_pdf: PathValue, destination: PathValue) -> None:
    """Render the first page of a PDF to a PNG file."""
    with pymupdf.open(source_pdf) as document:  # type: ignore[no-untyped-call]
        page = document.load_page(0)
        page.get_pixmap().save(destination)


def resize_to_width(
    source: PathValue,
    destination: PathValue,
    width: int,
    *,
    optimize: bool = False,
    quality: int | None = None,
) -> None:
    """Resize an image proportionally to a fixed width."""
    with Image.open(source) as image:
        height = round(image.height * width / image.width)
        resized = image.resize((width, height), Image.Resampling.LANCZOS)
        if quality is None:
            resized.save(destination, optimize=optimize)
        else:
            resized.save(destination, optimize=optimize, quality=quality)


def create_thumbnail(
    source: PathValue,
    destination: PathValue,
    base_width: int = 110,
) -> None:
    """Create a proportional cover thumbnail."""
    resize_to_width(source, destination, base_width)


def create_hero(
    source: PathValue,
    destination: PathValue,
    base_width: int = 1024,
) -> None:
    """Create a proportional, optimized hero image."""
    resize_to_width(source, destination, base_width, optimize=True, quality=95)
