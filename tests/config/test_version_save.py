"""
Version.save's version-number bump and the Article/Version relationship.
"""

from __future__ import annotations

import pytest

from stringprint.models import Article, Version

pytestmark = pytest.mark.django_db


@pytest.fixture
def article(org, doc_folder) -> Article:
    instance = Article.objects.create(org=org, slug="minimal-doc")
    instance.load_from_yaml(doc_folder("minimal-doc"))
    instance.load_from_file()
    return instance


class TestContent:
    def test_source_loading_creates_a_version(self, article: Article) -> None:
        version = article.content()
        assert isinstance(version, Version)
        assert version.article_id == article.pk

    def test_content_is_stable_across_calls(self, article: Article) -> None:
        assert article.content().pk == article.content().pk

    def test_load_from_file_populates_raw(self, article: Article) -> None:
        assert "Only Section" in article.content().raw


class TestVersionNumbering:
    def test_the_number_bumps_when_the_text_changes(self, article: Article) -> None:
        version = article.content()
        before = version.number

        version.raw = version.raw + "\n\nA new paragraph.\n"
        version.save()

        assert version.number == before + 1

    def test_the_number_holds_when_the_text_is_unchanged(
        self, article: Article
    ) -> None:
        version = article.content()
        before = version.number
        version.save()
        assert version.number == before

    def test_the_article_tracks_the_current_version(self, article: Article) -> None:
        version = article.content()
        version.raw = version.raw + "\n\nAnother paragraph.\n"
        version.save()

        article.refresh_from_db()
        assert article.current_version == version.number


class TestProcess:
    def test_processing_populates_sections(self, article: Article) -> None:
        article.process()
        assert len(article.content().sections) == 1

    def test_processing_clears_the_needs_processing_flag(
        self, article: Article
    ) -> None:
        article.needs_processing = True
        article.process()
        article.refresh_from_db()
        assert article.needs_processing is False

    def test_processing_sets_has_notes_only_when_asides_are_present(
        self, article: Article, process_doc
    ) -> None:
        article.process()
        assert article.content().has_notes is False
        assert process_doc("kitchen-sink").content().has_notes is True
