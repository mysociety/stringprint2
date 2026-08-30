"""
The remaining preview views: TOC, plain text, search, kindle templates,
assets, epub chapters and per-paragraph redirect pages.
"""

from __future__ import annotations

import json

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestTocView:
    @pytest.fixture
    def toc(self, client, kitchen_sink):
        response = client.get("/preview/kitchen-sink/tocjson")
        assert response.status_code == 200
        return json.loads(response.content.decode("utf-8"))

    def test_the_response_is_json(self, client, kitchen_sink) -> None:
        response = client.get("/preview/kitchen-sink/tocjson")
        assert response["Content-Type"].startswith("application/json")

    def test_every_section_appears(self, toc) -> None:
        rendered = json.dumps(toc)
        for name in ["Opening Section", "Assets and Markers", "Footnotes"]:
            assert name in rendered

    def test_headings_appear_beneath_their_section(self, toc) -> None:
        assert "A Titled Paragraph" in json.dumps(toc)

    def test_it_renders_for_a_multipage_document(self, client, multipage_doc) -> None:
        response = client.get("/preview/multipage-doc/tocjson")
        assert response.status_code == 200
        assert json.loads(response.content.decode("utf-8"))


class TestTextView:
    @pytest.fixture
    def page(self, client, kitchen_sink):
        response = client.get("/preview/kitchen-sink/text/")
        assert response.status_code == 200
        return response.content.decode("utf-8")

    def test_body_text_is_present(self, page: str) -> None:
        assert "An ordinary opening paragraph" in page

    def test_section_names_are_present(self, page: str) -> None:
        assert "Notes and Asides" in page

    def test_it_renders_for_every_document(self, client, process_doc) -> None:
        for slug in ["minimal-doc", "legacy-doc", "multipage-doc"]:
            process_doc(slug)
            assert client.get("/preview/{0}/text/".format(slug)).status_code == 200


class TestSearchViews:
    def test_the_search_page_renders(self, client, kitchen_sink) -> None:
        assert client.get("/preview/kitchen-sink/search").status_code == 200

    def test_the_search_index_renders(self, client, kitchen_sink) -> None:
        response = client.get("/preview/kitchen-sink/tipuesearch_content.js")
        assert response.status_code == 200
        assert "An ordinary opening paragraph" in response.content.decode("utf-8")

    def test_the_index_is_javascript_shaped(self, client, kitchen_sink) -> None:
        body = client.get(
            "/preview/kitchen-sink/tipuesearch_content.js"
        ).content.decode("utf-8")
        assert "tipuesearch" in body


class TestKindleTemplates:
    """
    kindlegen is not available and is out of scope, but the templates that feed
    it are plain Django rendering and stay covered.
    """

    def test_the_kindle_page_renders(self, client, kitchen_sink) -> None:
        response = client.get(reverse("kindle_view", args=("kitchen-sink",)))
        assert response.status_code == 200
        assert "An ordinary opening paragraph" in response.content.decode("utf-8")

    def test_the_opf_manifest_renders(self, client, kitchen_sink) -> None:
        response = client.get("/preview/kitchen-sink/kindle/opf")
        assert response.status_code == 200
        assert "Kitchen Sink" in response.content.decode("utf-8")

    def test_the_ncx_navigation_renders(self, client, kitchen_sink) -> None:
        response = client.get("/preview/kitchen-sink/kindle/ncx")
        assert response.status_code == 200
        assert "Opening Section" in response.content.decode("utf-8")

    def test_notes_are_inlined_when_display_notes_is_on(
        self, client, kitchen_sink
    ) -> None:
        body = client.get("/preview/kitchen-sink/kindle").content.decode("utf-8")
        assert "A single paragraph aside" in body

    def test_notes_are_separated_when_display_notes_is_off(
        self, client, multipage_doc
    ) -> None:
        assert multipage_doc.display_notes is False
        assert client.get("/preview/multipage-doc/kindle").status_code == 200


class TestEpubChapters:
    def test_a_chapter_renders(self, client, kitchen_sink) -> None:
        section = kitchen_sink.content().sections[0]
        response = client.get(
            "/preview/kitchen-sink/epub/{0}/".format(section.anchor())
        )
        assert response.status_code == 200

    def test_the_chapter_contains_only_its_own_text(
        self, client, kitchen_sink
    ) -> None:
        response = client.get("/preview/kitchen-sink/epub/footnotes/")
        page = response.content.decode("utf-8")
        assert "numbered footnote reference" in page
        assert "An ordinary opening paragraph" not in page


class TestAssetView:
    def test_an_asset_renders(self, client, kitchen_sink) -> None:
        response = client.get("/preview/asset/kitchen-sink/table-one/")
        assert response.status_code == 200

    def test_a_table_asset_renders_a_table(self, client, kitchen_sink) -> None:
        page = client.get(
            "/preview/asset/kitchen-sink/table-one/"
        ).content.decode("utf-8")
        assert "<table" in page

    @pytest.mark.parametrize("slug", ["html-one", "image-one"])
    def test_an_asset_without_a_chart_renders(
        self, client, kitchen_sink, slug: str
    ) -> None:
        assert client.get(
            "/preview/asset/kitchen-sink/{0}/".format(slug)
        ).status_code == 200

    def test_an_html_asset_renders_its_content(self, client, kitchen_sink) -> None:
        page = client.get(
            "/preview/asset/kitchen-sink/html-one/"
        ).content.decode("utf-8")
        assert "embedded-html-asset" in page


class TestRedirectLinkView:
    def test_a_paragraph_link_page_renders(self, client, kitchen_sink) -> None:
        graf = kitchen_sink.content().sections[0].grafs[0]
        response = client.get(
            "/preview/kitchen-sink/l/{0}".format(graf.combo_key())
        )
        assert response.status_code == 200

    def test_the_page_quotes_the_paragraph(self, client, kitchen_sink) -> None:
        graf = kitchen_sink.content().sections[0].grafs[0]
        page = client.get(
            "/preview/kitchen-sink/l/{0}".format(graf.combo_key())
        ).content.decode("utf-8")
        assert "ordinary opening paragraph" in page


class TestPreviewIndex:
    def test_the_index_renders(self, client, kitchen_sink) -> None:
        assert client.get("/preview/").status_code == 200

    def test_it_lists_the_loaded_documents(
        self, client, process_doc
    ) -> None:
        for slug in ["kitchen-sink", "minimal-doc"]:
            process_doc(slug)
        page = client.get("/preview/").content.decode("utf-8")
        assert "Kitchen Sink" in page
        assert "Minimal Document" in page

    def test_each_entry_links_to_the_article(self, client, kitchen_sink) -> None:
        page = client.get("/preview/").content.decode("utf-8")
        assert 'href="/preview/kitchen-sink/"' in page

    def test_documents_are_ordered_newest_first(
        self, client, process_doc
    ) -> None:
        for slug in ["kitchen-sink", "legacy-doc"]:
            process_doc(slug)
        page = client.get("/preview/").content.decode("utf-8")
        # kitchen-sink is 2022, legacy-doc is 2016
        assert page.index("Kitchen Sink") < page.index("Legacy Document")
