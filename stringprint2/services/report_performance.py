"""
Measure the structural cost of rendered long-form reports.
"""

from __future__ import annotations

from html.parser import HTMLParser

from pydantic import BaseModel, ConfigDict


class ReportMarkupMetrics(BaseModel):
    """
    Summarise HTML size and DOM growth for one rendered report.
    """

    model_config = ConfigDict(frozen=True)

    html_bytes: int
    element_count: int
    paragraph_count: int

    @property
    def elements_per_paragraph(self) -> float:
        """
        Return structural growth per canonical paragraph row.
        """
        if self.paragraph_count == 0:
            return 0
        return self.element_count / self.paragraph_count


class ReportMarkupParser(HTMLParser):
    """
    Count elements and canonical paragraph rows without building another DOM.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.element_count = 0
        self.paragraph_count = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.element_count += 1
        if any(name == "data-paragraph-order" for name, _ in attrs):
            self.paragraph_count += 1

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.handle_starttag(tag, attrs)


def measure_report_markup(html: str) -> ReportMarkupMetrics:
    """
    Measure one rendered report without browser-specific timing noise.
    """
    parser = ReportMarkupParser()
    parser.feed(html)
    return ReportMarkupMetrics(
        html_bytes=len(html.encode()),
        element_count=parser.element_count,
        paragraph_count=parser.paragraph_count,
    )
