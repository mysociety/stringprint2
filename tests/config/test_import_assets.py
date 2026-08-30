"""
Article.import_assets - assets.yaml into Asset rows.

Covers all four content_type branches, the alt_text fallback, longdesc
rendering, and the derived image files that create_responsive/create_tiny
produce.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from stringprint.models import Article, Asset

pytestmark = pytest.mark.django_db


@pytest.fixture
def assets(load_doc):
    article = load_doc("kitchen-sink")
    return {asset.slug: asset for asset in article.assets.all()}


class TestLoading:
    def test_every_declared_asset_is_created(self, assets) -> None:
        assert set(assets) == {
            "image-one",
            "image-two",
            "image-three",
            "table-one",
            "table-no-header-one",
            "html-one",
        }

    def test_a_missing_assets_yaml_is_not_an_error(self, load_doc) -> None:
        assert load_doc("minimal-doc").assets.count() == 0

    def test_an_empty_assets_yaml_creates_nothing(self, load_doc) -> None:
        assert load_doc("legacy-doc").assets.count() == 0

    def test_reimporting_does_not_duplicate(self, load_doc, doc_folder) -> None:
        article = load_doc("kitchen-sink")
        before = article.assets.count()
        article.import_assets(Path(doc_folder("kitchen-sink"), "assets"), False)
        assert article.assets.count() == before


class TestContentTypes:
    def test_an_image_becomes_an_image_asset(self, assets) -> None:
        asset = assets["image-one"]
        assert asset.type == Asset.IMAGE
        assert asset.image.name == "{0}_image-one.png".format(asset.article_id)

    def test_a_table_becomes_a_chart_asset(self, assets) -> None:
        asset = assets["table-one"]
        assert asset.type == Asset.CHART
        assert asset.chart.chart_type == "table_chart"
        assert len(asset.chart.rows) == 4

    def test_table_no_header_sets_the_flag_and_normalises_the_type(
        self, assets
    ) -> None:
        asset = assets["table-no-header-one"]
        assert asset.type == Asset.CHART
        assert asset.no_header is True

    def test_an_ordinary_table_does_not_set_the_flag(self, assets) -> None:
        assert assets["table-one"].no_header is False

    def test_html_content_is_read_off_disk(self, assets) -> None:
        asset = assets["html-one"]
        assert asset.type == Asset.RAW_HTML
        assert "embedded-html-asset" in asset.content


class TestTextFields:
    def test_alt_text_is_used_when_present(self, assets) -> None:
        assert assets["image-one"].alt_text == "Alt text for image one"

    def test_an_absent_alt_text_falls_back_to_the_caption(self, assets) -> None:
        assert assets["image-three"].alt_text == "Caption with no alt_text key at all"

    def test_an_empty_alt_text_stays_empty(self, assets) -> None:
        """
        The fallback is a.get("alt_text", a.get("caption", "")), so it only
        fires when the key is absent. An explicitly empty alt_text is kept as
        an empty string rather than borrowing the caption.
        """
        assert assets["image-two"].alt_text == ""
        assert assets["image-two"].caption == "Caption doubles as alt text"

    def test_the_caption_is_kept_separately(self, assets) -> None:
        assert assets["image-one"].caption == "A caption for image one"

    def test_longdesc_is_rendered_as_markdown(self, assets) -> None:
        content = assets["table-one"].content
        assert content.count("<p>") == 2, "single newlines are doubled first"
        assert "First line of the long description." in content

    def test_assets_without_a_longdesc_have_empty_content(self, assets) -> None:
        assert assets["image-one"].content == ""


class TestDerivedImages:
    WIDTHS = [768, 992, 1200, 1440, 1920]

    def test_a_responsive_variant_exists_for_every_width(
        self, assets, media_root
    ) -> None:
        asset = assets["image-one"]
        for width in self.WIDTHS:
            name = asset.get_responsive_image_name(width)
            assert (media_root / name).exists(), name

    def test_a_webp_variant_accompanies_each_size(self, assets, media_root) -> None:
        asset = assets["image-one"]
        for width in self.WIDTHS:
            name = asset.get_responsive_image_name(width)
            assert (media_root / name).with_suffix(".webp").exists()

    def test_the_image_ratio_and_colour_are_recorded(self, assets) -> None:
        extra = assets["image-one"].extra_values
        assert extra["ratio"] > 0
        assert extra["color"].startswith("#")

    def test_get_all_files_lists_every_derived_file(self, assets) -> None:
        files = list(assets["image-one"].get_all_files())
        assert len(files) >= len(self.WIDTHS)

    def test_an_image_smaller_than_every_width_is_not_upscaled(
        self, assets, media_root
    ) -> None:
        from PIL import Image

        asset = assets["image-three"]
        for width in self.WIDTHS:
            path = media_root / asset.get_responsive_image_name(width)
            assert Image.open(str(path)).size == (400, 300)

    def test_a_non_image_asset_has_no_image(self, assets) -> None:
        assert not assets["table-one"].image


class TestSearchAndEscapeHelpers:
    def test_search_name_prefers_the_caption(self, assets) -> None:
        assert assets["image-one"].search_name() == "A caption for image one"

    def test_search_name_falls_back_to_alt_text(self) -> None:
        assert Asset(caption="", alt_text="Some alt").search_name() == "Some alt"

    def test_escape_text_strips_paragraph_tags_and_brackets(self) -> None:
        assert Asset(content="<p>a [b]</p>").escape_text() == "a b"
