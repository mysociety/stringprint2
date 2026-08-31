"""
The main document page.

These go through the Django test client, so they exercise the url conf, the
useful_inkleby view machinery, the template chain and the org template
override together.
"""

from __future__ import annotations

import pytest
from django.conf import settings
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture
def page(client, kitchen_sink):
    response = client.get(reverse("article_view", args=(kitchen_sink.slug,)))
    assert response.status_code == 200
    return response.content.decode("utf-8")


class TestRendering:
    def test_the_page_renders(self, client, kitchen_sink) -> None:
        response = client.get(reverse("article_view", args=("kitchen-sink",)))
        assert response.status_code == 200

    def test_every_fixture_document_renders(self, client, process_doc) -> None:
        for slug in ["minimal-doc", "kitchen-sink", "legacy-doc", "multipage-doc"]:
            process_doc(slug)
            response = client.get(reverse("article_view", args=(slug,)))
            assert response.status_code == 200, slug

    def test_an_unknown_slug_raises(self, client) -> None:
        from stringprint.models import Article

        with pytest.raises(Article.DoesNotExist):
            client.get(reverse("article_view", args=("no-such-document",)))


class TestContent:
    def test_the_title_appears(self, page: str) -> None:
        assert "Kitchen Sink" in page

    def test_body_text_appears(self, page: str) -> None:
        assert "An ordinary opening paragraph" in page

    def test_section_headings_appear(self, page: str) -> None:
        assert "Notes and Asides" in page

    def test_footnote_content_appears(self, page: str) -> None:
        assert "The first footnote" in page

    def test_asides_are_rendered(self, page: str) -> None:
        assert "A single paragraph aside" in page

    def test_a_table_asset_is_rendered_as_a_table(self, page: str) -> None:
        assert "<table" in page

    def test_an_html_asset_is_embedded(self, page: str) -> None:
        assert "embedded-html-asset" in page

    def test_an_image_asset_is_referenced(self, page: str) -> None:
        assert "image-one" in page

    def test_raw_markers_never_reach_the_page(self, page: str) -> None:
        for marker in ["[asset:", "[tag:", "[para:", "[page:", "[catchup:", "[^"]:
            assert marker not in page, marker


class TestOrgTemplateOverride:
    def test_the_org_template_is_used(self, page: str) -> None:
        assert "ORG_TEMPLATE_OVERRIDE_MARKER" in page

    def test_the_override_still_extends_the_app_template(self, page: str) -> None:
        # content from the app template that the override does not replace
        assert "Kitchen Sink" in page
        assert "<html" in page


class TestSocialSettings:
    def test_open_graph_tags_are_rendered(self, page: str) -> None:
        assert 'property="og:title"' in page
        assert 'property="og:description"' in page

    def test_the_org_name_is_used_as_the_site_name(self, page: str) -> None:
        assert "Test Org" in page

    def test_the_twitter_handle_is_used(self, page: str) -> None:
        assert "testorg" in page


class TestMultipage:
    def test_the_first_page_renders(self, client, multipage_doc) -> None:
        response = client.get(reverse("article_view", args=("multipage-doc",)))
        assert response.status_code == 200

    def test_each_section_has_its_own_page(self, client, multipage_doc) -> None:
        for section in multipage_doc.content().sections:
            response = client.get("/preview/multipage-doc/{0}".format(section.anchor()))
            assert response.status_code == 200, section.anchor()

    def test_a_section_page_shows_that_section(self, client, multipage_doc) -> None:
        response = client.get("/preview/multipage-doc/second-chapter")
        page = response.content.decode("utf-8")
        assert "opening paragraph of the first chapter" not in page

    def test_a_cross_chapter_tag_link_is_rewritten(
        self, client, multipage_doc
    ) -> None:
        """
        In multipage mode a bare '#tag.name' fragment would resolve against
        the current chapter. It is rewritten to the page holding the tagged
        paragraph - chapter one here - with the fragment kept on the end.
        """
        response = client.get("/preview/multipage-doc/second-chapter")
        page = response.content.decode("utf-8")
        assert 'href="/preview/multipage-doc/#tag.crosstag"' in page
        assert 'href="#tag.crosstag"' not in page

    def test_a_cross_chapter_anchor_link_is_rewritten(
        self, client, multipage_doc
    ) -> None:
        response = client.get("/preview/multipage-doc/second-chapter")
        page = response.content.decode("utf-8")
        assert 'href="/preview/multipage-doc/#first-chapter"' in page

    def test_links_are_not_rewritten_in_single_page_mode(
        self, client, kitchen_sink
    ) -> None:
        response = client.get("/preview/kitchen-sink/")
        page = response.content.decode("utf-8")
        assert 'href="#opening-section"' in page


class TestScreenshotMode:
    def test_the_screenshot_parameter_forces_single_page(
        self, client, multipage_doc
    ) -> None:
        response = client.get(
            "/preview/multipage-doc/",
            {"id": str(multipage_doc.id), "screenshot": "true"},
        )
        assert response.status_code == 200
        page = response.content.decode("utf-8")
        # all chapters on one page
        assert "opening paragraph of the first chapter" in page
        assert "different chapter" in page
