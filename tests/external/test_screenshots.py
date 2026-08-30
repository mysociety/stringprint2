"""
Article.export_paragraph_images - the per-paragraph social cards.

In production this drives headless Chrome against a preview server the CLI
spawns on 127.0.0.1:8000. Chrome.get_driver is the only place the driver is
built, so replacing it lets the surrounding logic run for real: the skip
filters, the scroll, the crop arithmetic and the output filenames.

The BAKE_SERVER address is a local inside the method, so there is no seam for
pointing it at a live_server; a real end-to-end run is out of scope here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.external]


@pytest.fixture
def folder(tmp_path) -> Path:
    destination = tmp_path / "paragraphs"
    destination.mkdir()
    return destination


class TestImageExport:
    def test_an_image_is_written_per_eligible_graf(
        self, kitchen_sink, fake_chrome, folder
    ) -> None:
        kitchen_sink.export_paragraph_images(str(folder))
        assert list(folder.glob("*.png"))

    def test_images_are_named_by_combo_key(
        self, kitchen_sink, fake_chrome, folder
    ) -> None:
        kitchen_sink.export_paragraph_images(str(folder))
        keys = {
            graf.combo_key()
            for section in kitchen_sink.content().sections
            for graf in section.grafs
        }
        for path in folder.glob("*.png"):
            assert path.stem in keys

    def test_the_crop_is_the_social_card_size(
        self, kitchen_sink, fake_chrome, folder
    ) -> None:
        from PIL import Image

        kitchen_sink.export_paragraph_images(str(folder))
        path = sorted(folder.glob("*.png"))[0]
        assert Image.open(str(path)).size == (1216, 630)

    def test_the_screenshot_url_asks_for_screenshot_mode(
        self, kitchen_sink, fake_chrome, folder
    ) -> None:
        kitchen_sink.export_paragraph_images(str(folder))
        assert "screenshot=true" in fake_chrome.requested_url
        assert "127.0.0.1:8000" in fake_chrome.requested_url

    def test_the_window_is_sized_for_the_card(
        self, kitchen_sink, fake_chrome, folder
    ) -> None:
        kitchen_sink.export_paragraph_images(str(folder))
        assert fake_chrome.window_size == (1200, 800)


class TestSkipRules:
    def test_asset_grafs_are_skipped(
        self, kitchen_sink, fake_chrome, folder
    ) -> None:
        kitchen_sink.export_paragraph_images(str(folder))
        written = {path.stem for path in folder.glob("*.png")}
        asset_keys = {
            graf.combo_key()
            for section in kitchen_sink.content().sections
            for graf in section.grafs
            if "[asset:" in graf.plain_txt.lower()
        }
        assert not (asset_keys & written)

    def test_existing_images_are_left_alone_without_refresh(
        self, kitchen_sink, fake_chrome, folder
    ) -> None:
        kitchen_sink.export_paragraph_images(str(folder))
        first = sorted(path.name for path in folder.glob("*.png"))
        stamps = {path.name: path.stat().st_mtime_ns for path in folder.glob("*.png")}

        kitchen_sink.export_paragraph_images(str(folder))
        assert sorted(path.name for path in folder.glob("*.png")) == first
        for path in folder.glob("*.png"):
            assert path.stat().st_mtime_ns == stamps[path.name]

    def test_nothing_to_do_means_no_browser_is_started(
        self, kitchen_sink, fake_chrome, folder
    ) -> None:
        kitchen_sink.export_paragraph_images(str(folder))
        fake_chrome.requested_url = None
        kitchen_sink.export_paragraph_images(str(folder))
        assert fake_chrome.requested_url is None

    def test_a_missing_element_is_skipped_rather_than_fatal(
        self, kitchen_sink, monkeypatch, folder
    ) -> None:
        from stringprint.models import Chrome
        from tests.conftest import FakeDriver

        first_graf = kitchen_sink.content().sections[0].grafs[0]
        driver = FakeDriver(missing_orders=[first_graf.order])
        monkeypatch.setattr(Chrome, "driver", None)
        monkeypatch.setattr(Chrome, "get_driver", classmethod(lambda cls: driver))

        kitchen_sink.export_paragraph_images(str(folder))

        written = {path.stem for path in folder.glob("*.png")}
        assert first_graf.combo_key() not in written
        assert written, "the other paragraphs should still be exported"
