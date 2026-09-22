"""
DOM growth budgets for long-form report markup.
"""

from __future__ import annotations

import pytest

from stringprint2.services.report_performance import measure_report_markup

pytestmark = pytest.mark.django_db


def synthetic_report(paragraph_count: int) -> str:
    """
    Build canonical paragraph markup at representative report sizes.
    """
    paragraphs = "".join(
        f'<div class="content-row" id="1.{index}.key.start.end.letter" '
        f'data-paragraph-order="{index}" data-section="1">'
        f'<p id="p{index}">Paragraph {index}</p></div>'
        for index in range(paragraph_count)
    )
    return f"<main><section>{paragraphs}</section></main>"


@pytest.mark.parametrize("paragraph_count", [100, 500, 1_000])
def test_canonical_markup_scales_linearly(paragraph_count: int) -> None:
    metrics = measure_report_markup(synthetic_report(paragraph_count))

    assert metrics.paragraph_count == paragraph_count
    assert metrics.elements_per_paragraph < 2.1


def test_rendered_report_stays_within_dom_budget(client, kitchen_sink) -> None:
    html = client.get("/preview/kitchen-sink/").content.decode()
    metrics = measure_report_markup(html)

    assert metrics.paragraph_count > 0
    assert metrics.elements_per_paragraph < 12
    assert "noscript-anchor" not in html
    assert "position_key =" not in html
