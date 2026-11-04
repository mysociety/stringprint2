"""Explicit per-build presentation options and collected asset dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser


@dataclass(frozen=True)
class PublicationRenderContext:
    baking: bool = False
    site_root: str | None = None
    plain: bool = True
    epub: bool = False
    kindle: bool = False
    compressed_files: list[str] = field(default_factory=list, compare=False)

    def template_values(self) -> dict[str, object]:
        result: dict[str, object] = {
            "publication_render": self,
            "publication_bake": self.baking,
        }
        if self.site_root is not None:
            result["SITE_ROOT"] = self.site_root
        if self.baking:
            result.update(
                debug=False, plain=self.plain, epub=self.epub, kindle=self.kindle
            )
        return result

    def record_assets(self, fragment: str) -> None:
        collector = _AssetCollector()
        collector.feed(fragment)
        for url in collector.urls:
            if url not in self.compressed_files:
                self.compressed_files.append(url)


class _AssetCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attribute = "href" if tag == "link" else "src" if tag == "script" else None
        for name, value in attrs:
            if name == attribute and value:
                self.urls.append(value)
