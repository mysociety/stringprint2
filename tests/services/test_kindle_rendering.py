"""
Integration tests for staged Kindle rendering.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from stringprint.models import Asset
from stringprint2.services.kindle_rendering import render_kindle

pytestmark = pytest.mark.django_db


def test_kindle_render_uses_typed_process_arguments_and_copies_result(
    kitchen_sink,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def generate(arguments: list[str]) -> int:
        calls.append(arguments)
        Path(arguments[1]).with_suffix(".mobi").write_bytes(b"generated mobi")
        return 0

    result = render_kindle(
        kitchen_sink,
        tmp_path,
        use_temporary_directory=True,
        image_asset_type=Asset.IMAGE,
        chart_asset_type=Asset.CHART,
        runner=generate,
    )

    assert len(calls) == 1
    assert calls[0][1].endswith("kitchen-sink.opf")
    assert result.destination == tmp_path / "kitchen-sink.mobi"
    assert result.destination.read_bytes() == b"generated mobi"
    assert result.generated is True
    assert result.return_code == 0
    assert result.media_count > 0
