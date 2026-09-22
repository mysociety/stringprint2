"""
Article.load_from_yaml - the per-document settings.yaml reader.

This is where the legacy key aliases, the org default_values templating and
the extra_values routing all live, so it is the densest single method in the
config layer.
"""

from __future__ import annotations

import pytest

from stringprint.models import Article

pytestmark = pytest.mark.django_db


class TestFieldMapping:
    def test_plain_fields_are_set(self, load_doc) -> None:
        article = load_doc("kitchen-sink")
        assert article.title == "Kitchen Sink: A Study"
        assert article.subtitle == "Every feature in one document"
        assert article.short_title == "Kitchen Sink"
        assert article.authors == "Ada Example, Grace Example"
        assert article.cite_as == "Example, A. and Example, G."

    def test_the_publish_date_is_parsed(self, load_doc) -> None:
        assert str(load_doc("kitchen-sink").publish_date) == "2022-04-21"

    def test_booleans_are_set(self, load_doc) -> None:
        article = load_doc("kitchen-sink")
        assert article.display_notes is True
        assert article.display_footnotes_at_foot is True


class TestLegacyAliases:
    def test_sections_over_pages_becomes_multipage(self, load_doc) -> None:
        assert load_doc("kitchen-sink").multipage is False
        assert load_doc("multipage-doc").multipage is True

    def test_the_alias_key_is_not_kept(self, load_doc) -> None:
        assert "sections_over_pages" not in load_doc("kitchen-sink").extra_values

    def test_pdf_becomes_pdf_file(self, load_doc) -> None:
        assert load_doc("kitchen-sink").pdf_file == "kitchen-sink.pdf"

    def test_pdf_is_not_kept_as_an_extra_value(self, load_doc) -> None:
        assert "pdf" not in load_doc("kitchen-sink").extra_values

    def test_pdf_location_is_a_field_in_its_own_right(self, load_doc) -> None:
        article = load_doc("legacy-doc")
        assert article.pdf_location == "https://example.invalid/external/legacy.pdf"
        assert not article.pdf_file

    def test_pdf_file_is_cleared_when_the_key_disappears(self, org, doc_folder) -> None:
        article = Article.objects.create(
            org=org, slug="legacy-doc", pdf_file="stale.pdf"
        )
        article.load_from_yaml(doc_folder("legacy-doc"))
        assert article.pdf_file == ""


class TestExtraValues:
    def test_unknown_keys_go_to_extra_values(self, load_doc) -> None:
        extra = load_doc("kitchen-sink").extra_values
        assert extra["repo_slug"] == "kitchen-sink"
        assert extra["google_doc_url"].startswith("https://docs.google.com/")
        assert extra["unsplash_title_image_url"].startswith("https://unsplash.com/")

    def test_a_list_value_survives(self, load_doc) -> None:
        assert load_doc("legacy-doc").extra_values["files"] == ["extra_download.pdf"]

    def test_a_boolean_extra_survives(self, load_doc) -> None:
        assert load_doc("legacy-doc").extra_values["skip_epub"] is True

    def test_stale_extra_values_are_pruned(self, org, doc_folder) -> None:
        article = Article.objects.create(org=org, slug="minimal-doc")
        article.extra_values = {"gone_from_yaml": "x"}
        article.load_from_yaml(doc_folder("minimal-doc"))
        assert "gone_from_yaml" not in article.extra_values


class TestOrgDefaultValues:
    def test_defaults_are_injected_when_absent(self, load_doc) -> None:
        extra = load_doc("kitchen-sink").extra_values
        assert extra["repo_entry"] == (
            "https://example.invalid/publications/kitchen-sink"
        )

    def test_defaults_are_rendered_as_django_templates(self, load_doc) -> None:
        extra = load_doc("kitchen-sink").extra_values
        assert extra["bottom_iframe"] == (
            "https://example.invalid/embed/related:kitchen-sink"
        )

    def test_an_empty_value_in_the_document_suppresses_the_default(
        self, load_doc
    ) -> None:
        """
        Four production documents set `bottom_iframe:` with no value purely to
        stop the org default being templated in. The key is present, so the
        default is skipped, and the empty value is what lands.
        """
        assert not load_doc("legacy-doc").extra_values["bottom_iframe"]

    def test_defaults_still_apply_to_a_minimal_document(self, load_doc) -> None:
        extra = load_doc("minimal-doc").extra_values
        assert extra["repo_entry"].endswith("minimal-doc")
        assert extra["bottom_iframe"].endswith("minimal-doc")


class TestHeaderImage:
    def test_a_header_image_is_attached(self, load_doc) -> None:
        article = load_doc("kitchen-sink")
        assert article.images.filter(title_image=True).count() == 1

    def test_the_size_is_carried_across(self, load_doc) -> None:
        header = load_doc("kitchen-sink").images.get(title_image=True)
        assert header.size == 6

    def test_background_size_becomes_minus_one(self, load_doc) -> None:
        header = load_doc("multipage-doc").images.get(title_image=True)
        assert header.size == -1

    def test_the_image_is_renamed_after_the_slug(self, load_doc) -> None:
        header = load_doc("kitchen-sink").images.get(title_image=True)
        assert header.image.name == "kitchen-sink.png"

    def test_a_document_without_a_header_gets_no_image(self, load_doc) -> None:
        assert load_doc("minimal-doc").images.count() == 0


class TestBookCover:
    def test_a_book_cover_is_loaded(self, load_doc) -> None:
        assert load_doc("kitchen-sink").book_cover

    def test_no_book_cover_key_leaves_it_unset(self, load_doc) -> None:
        assert not load_doc("minimal-doc").book_cover


class TestDerivedValues:
    def test_production_url_defaults_from_the_org_publish_root(self, load_doc) -> None:
        article = load_doc("kitchen-sink")
        assert article.production_url == (
            "https://example.invalid/html/kitchen-sink/"
        )

    def test_file_source_is_resolved_against_the_document_folder(
        self, load_doc, doc_folder
    ) -> None:
        article = load_doc("kitchen-sink")
        assert article.file_source == str(doc_folder("kitchen-sink") / "document.md")

    def test_last_updated_is_stamped(self, load_doc) -> None:
        assert load_doc("kitchen-sink").last_updated is not None

    def test_the_article_is_saved(self, load_doc) -> None:
        article = load_doc("kitchen-sink")
        assert Article.objects.filter(pk=article.pk).exists()
