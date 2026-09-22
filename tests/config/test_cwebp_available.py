"""
Named first on purpose.

HeaderMixin.create_responsive raises ValueError when cwebp produces no output,
which would otherwise fail every test that loads an image asset at once and
bury the cause. This gives that failure a single obvious home.
"""

from __future__ import annotations

from pathlib import Path

from webptools import webplib as webp


def test_cwebp_produces_output(tmp_path: Path) -> None:
    source = (
        Path(__file__).parent.parent
        / "fixtures"
        / "doc_source"
        / "_docs"
        / "kitchen-sink"
        / "assets"
        / "image-one.png"
    )
    destination = tmp_path / "out.webp"

    result = webp.cwebp(
        str(source), str(destination), "-lossless -q 100 -resize 200 112"
    )

    assert destination.exists(), "cwebp produced no output: {0}".format(result)
    assert destination.stat().st_size > 0
