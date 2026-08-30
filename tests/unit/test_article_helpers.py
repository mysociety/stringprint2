"""
Article's pure display helpers, on unsaved instances.

`baking` is not a model field - the bake views inject it through
article_settings_override - so tests that want the baked branch set it by hand.
"""

from __future__ import annotations

import datetime

import pytest
from django.conf import settings

from stringprint.models import Article


def article(**kwargs) -> Article:
    return Article(**kwargs)


class TestSplitTitle:
    def test_a_colon_splits_the_title(self) -> None:
        assert article(title="Main: Sub").split_title() == "Main:"

    def test_a_question_mark_splits_the_title(self) -> None:
        assert article(title="Really? Yes").split_title() == "Really?"

    def test_an_explicit_subtitle_suppresses_splitting(self) -> None:
        instance = article(title="Main: Sub", subtitle="Given")
        assert instance.split_title() == "Main: Sub"

    def test_an_unsplittable_title_is_returned_whole(self) -> None:
        assert article(title="Just A Title").split_title() == "Just A Title"

    def test_hyphens_become_non_breaking(self) -> None:
        assert article(title="Non-breaking").split_title() == "Non&#8209;breaking"

    def test_the_hyphen_swap_happens_before_splitting(self) -> None:
        assert article(title="A-B: C").split_title() == "A&#8209;B:"


class TestSplitSubtitle:
    def test_an_explicit_subtitle_wins(self) -> None:
        assert article(title="Main: Sub", subtitle="Given").split_subtitle() == "Given"

    def test_a_colon_gives_the_tail(self) -> None:
        assert article(title="Main: Sub").split_subtitle() == "Sub"

    def test_a_question_mark_gives_the_tail(self) -> None:
        assert article(title="Really? Yes").split_subtitle() == "Yes"

    def test_an_unsplittable_title_gives_nothing(self) -> None:
        assert article(title="Just A Title").split_subtitle() is None

    def test_the_hyphen_swap_does_not_apply_to_the_subtitle(self) -> None:
        assert article(title="A: B-C").split_subtitle() == "B-C"


class TestYear:
    def test_uses_the_publish_date(self) -> None:
        assert article(publish_date=datetime.date(2016, 5, 1)).year() == 2016

    def test_falls_back_to_now(self) -> None:
        assert article(publish_date=None).year() == datetime.datetime.now().year


class TestUrl:
    def test_live_url_goes_through_the_url_conf(self) -> None:
        result = article(slug="a-doc").url()
        assert result.startswith(settings.SITE_ROOT)
        assert "a-doc" in result

    def test_a_section_is_included(self) -> None:
        assert "a-doc/chapter" in article(slug="a-doc").url("chapter")

    def test_baking_returns_a_relative_directory(self) -> None:
        instance = article(slug="a-doc")
        instance.baking = True
        assert instance.url() == "./"

    def test_baking_with_a_section_returns_a_relative_file(self) -> None:
        instance = article(slug="a-doc")
        instance.baking = True
        assert instance.url("chapter") == "./chapter.html"


class TestPdfUrl:
    def test_an_external_location_wins(self) -> None:
        instance = article(slug="a-doc", pdf_location="https://example.invalid/x.pdf")
        assert instance.pdf_url() == "https://example.invalid/x.pdf"

    def test_a_local_file_is_resolved_against_the_article_url(self) -> None:
        instance = article(slug="a-doc", pdf_file="a-doc.pdf")
        instance.baking = True
        assert instance.pdf_url() == "./a-doc.pdf"

    def test_neither_gives_nothing(self) -> None:
        assert article(slug="a-doc").pdf_url() is None

    def test_the_external_location_beats_a_local_file(self) -> None:
        instance = article(
            slug="a-doc", pdf_file="a-doc.pdf", pdf_location="https://e.invalid/x.pdf"
        )
        assert instance.pdf_url() == "https://e.invalid/x.pdf"


class TestSearchUrl:
    def test_live_search_url(self) -> None:
        instance = article(slug="a-doc")
        instance.baking = False
        assert instance.search_url() == "search"

    def test_baked_search_url(self) -> None:
        instance = article(slug="a-doc")
        instance.baking = True
        assert instance.search_url() == "search.html"


class TestReprocessing:
    @pytest.mark.parametrize(
        "needs,reprocess,expected",
        [(True, False, True), (False, True, True), (False, False, False)],
    )
    def test_reprocessing_is_either_flag(
        self, needs: bool, reprocess: bool, expected: bool
    ) -> None:
        instance = article(needs_processing=needs, reprocess_source=reprocess)
        assert bool(instance.reprocessing()) is expected
