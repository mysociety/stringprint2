"""Tests for publication PDF and image operations."""

from __future__ import annotations

import fitz
from PIL import Image

from stringprint2.media_files import (
    create_hero,
    create_thumbnail,
    merge_pdfs,
    pdf_page_to_png,
)


def make_pdf(path, pages: int) -> None:
    """Create a small PDF fixture."""
    with fitz.open() as document:
        for page_number in range(pages):
            page = document.new_page(width=100, height=120)
            page.insert_text((10, 20), f"page {page_number}")
        document.save(path)


def test_merge_pdfs_uses_cover_and_requested_content_pages(tmp_path) -> None:
    """The cover replaces content pages before start_page."""
    front = tmp_path / "front.pdf"
    contents = tmp_path / "contents.pdf"
    output = tmp_path / "merged.pdf"
    make_pdf(front, 1)
    make_pdf(contents, 3)

    merge_pdfs(front, contents, output, start_page=1)

    with fitz.open(output) as merged:
        assert merged.page_count == 3
        assert "page 0" in merged[0].get_text()
        assert "page 1" in merged[1].get_text()


def test_pdf_page_to_png_renders_the_cover(tmp_path) -> None:
    """A PDF cover can be rendered for subsequent image resizing."""
    source = tmp_path / "cover.pdf"
    output = tmp_path / "cover.png"
    make_pdf(source, 1)

    pdf_page_to_png(source, output)

    with Image.open(output) as image:
        assert image.width == 100
        assert image.height == 120


def test_thumbnail_and_hero_preserve_aspect_ratio(tmp_path) -> None:
    """Both output variants resize to their configured widths."""
    source = tmp_path / "source.png"
    thumbnail = tmp_path / "thumbnail.png"
    hero = tmp_path / "hero.png"
    Image.new("RGB", (200, 100), "red").save(source)

    create_thumbnail(source, thumbnail)
    create_hero(source, hero)

    with Image.open(thumbnail) as image:
        assert image.size == (110, 55)
    with Image.open(hero) as image:
        assert image.size == (1024, 512)
