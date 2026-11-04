"""
Integration tests for staged Kindle rendering.
"""

from __future__ import annotations

from pathlib import Path
from django.conf import settings

import pytest

from stringprint.models import Asset
from stringprint2.services.kindle_rendering import render_kindle

pytestmark = pytest.mark.django_db


def test_kindle_render_uses_typed_process_arguments_and_copies_result(
    kitchen_sink,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []
    original = (settings.STATIC_URL, settings.DEBUG)

    def generate(arguments: list[str]) -> int:
        assert (settings.STATIC_URL, settings.DEBUG) == original
        assert (
            'href="css/kindle.css"'
            in Path(arguments[1]).with_name("text.html").read_text()
        )
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
    assert (settings.STATIC_URL, settings.DEBUG) == original


def test_missing_kindle_generator_has_an_actionable_error(
    kitchen_sink, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Explicit Kindle requests explain how to configure the unavailable binary.
    """
    monkeypatch.setattr(
        "stringprint2.services.kindle_rendering.shutil.which", lambda value: None
    )
    with pytest.raises(FileNotFoundError, match="KINDLEGEN_LOC"):
        render_kindle(
            kitchen_sink,
            tmp_path,
            image_asset_type=Asset.IMAGE,
            chart_asset_type=Asset.CHART,
        )


def test_generator_failure_does_not_report_success(
    kitchen_sink, tmp_path: Path
) -> None:
    """
    A failed subprocess cannot produce a successful operation result.
    """
    with pytest.raises(RuntimeError, match="Kindle generation failed"):
        render_kindle(
            kitchen_sink,
            tmp_path,
            image_asset_type=Asset.IMAGE,
            chart_asset_type=Asset.CHART,
            runner=lambda arguments: 2,
        )
