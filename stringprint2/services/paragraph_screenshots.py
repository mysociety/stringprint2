"""Export social cards with an explicitly scoped browser session."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


@dataclass(frozen=True)
class ScreenshotParagraph:
    order: int
    key: str
    text: str


@contextmanager
def paragraph_browser() -> Iterator[Page]:
    """Release the browser even when navigation or a screenshot fails."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            yield browser.new_page()
        finally:
            browser.close()


def export_paragraph_images(
    preview_url: str,
    paragraphs: Sequence[ScreenshotParagraph],
    folder: Path,
    *,
    refresh: bool = False,
) -> None:
    targets = [
        paragraph
        for paragraph in paragraphs
        if paragraph.text.strip()
        and "[asset:" not in paragraph.text.lower()
        and (refresh or not (folder / f"{paragraph.key}.png").exists())
    ]
    if not targets:
        return
    folder.mkdir(parents=True, exist_ok=True)
    with paragraph_browser() as page:
        page.set_viewport_size({"width": 1200, "height": 800})
        page.goto(preview_url, timeout=60_000)
        for paragraph in targets:
            locator = page.locator(
                f'.content-row[data-paragraph-order="{paragraph.order}"]'
            )
            if locator.count() == 0:
                continue
            box = locator.bounding_box()
            if box is None:
                continue
            page.evaluate(f"window.scrollTo(0, {box['y'] - 50});")
            page.screenshot(
                path=folder / f"{paragraph.key}.png",
                clip={"x": box["x"] - 30, "y": 42, "width": 1216, "height": 630},
            )
