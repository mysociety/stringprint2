"""
Section - navigation, naming and the graf assembly generator.

nav_url and get_grafs need a stand-in version/article. Note that `baking` and
`search` are NOT model fields: the views inject them through
article_settings_override, so anything constructing an article by hand has to
set them explicitly.
"""

from __future__ import annotations

import pytest

from stringprint.tools.deepink import Graf, Section


class FakeArticle:
    def __init__(self, multipage=False, baking=False, search=False, display_notes=True):
        self.multipage = multipage
        self.baking = baking
        self.search = search
        self.display_notes = display_notes

    def url(self, anchor=""):
        return "/article/{0}".format(anchor)


class FakeVersion:
    def __init__(self, article, sections=None):
        self.article = article
        self.sections = sections or []


def build(sections, **article_kwargs):
    article = FakeArticle(**article_kwargs)
    version = FakeVersion(article, sections)
    for section in sections:
        section._version = version
        section._article = article
    return version


class TestNaming:
    def test_anchor_slugifies_the_name(self) -> None:
        assert Section(name="A Section Name").anchor() == "a-section-name"

    def test_an_empty_name_anchors_to_start(self) -> None:
        assert Section(name="").anchor() == "start"

    def test_an_offset_is_appended(self) -> None:
        assert Section(name="Repeated", anchor_offset="1").anchor() == "repeated_1"

    def test_reduced_name_truncates_past_twenty_five_characters(self) -> None:
        long = "A" * 30
        assert Section(name=long).reduced_name() == "A" * 25 + "[...]"

    def test_reduced_name_leaves_short_names_alone(self) -> None:
        assert Section(name="Short").reduced_name() == "Short"


class TestGrafCollections:
    def test_has_grafs_counts_grafs_with_real_text(self) -> None:
        section = Section(grafs=[Graf(plain_txt="real text"), Graf(plain_txt="")])
        assert section.has_grafs() == 1

    def test_has_grafs_is_false_when_all_are_empty(self) -> None:
        assert Section(grafs=[Graf(plain_txt="")]).has_grafs() is False

    def test_has_grafs_is_false_with_no_grafs(self) -> None:
        assert Section(grafs=[]).has_grafs() is False

    def test_first_graf_id_is_the_first_order(self) -> None:
        assert Section(grafs=[Graf(order=4), Graf(order=5)]).first_graf_id() == 4

    def test_first_graf_id_is_none_when_empty(self) -> None:
        assert Section(grafs=[]).first_graf_id() is None

    def test_grafs_with_titles_filters(self) -> None:
        section = Section(grafs=[Graf(title="T"), Graf(title="")])
        assert len(section.grafs_with_titles()) == 1

    def test_save_process_builds_the_tag_index(self) -> None:
        section = Section(order=3, grafs=[Graf(tag="one"), Graf(tag=None)])
        section.save_process()
        assert section.tagged == {"one": 3}

    def test_used_assets_collects_graf_assets(self) -> None:
        section = Section(grafs=[Graf(asset=1), Graf(asset=None), Graf(asset=2)])
        assert section.used_assets() == [1, 2]

    def test_used_assets_includes_the_header_asset(self) -> None:
        section = Section(grafs=[Graf(asset=1)], header_asset=9)
        assert section.used_assets() == [1, 9]


class TestSiblings:
    def test_next_and_prev_walk_the_order(self) -> None:
        first, second = Section(order=1), Section(order=2)
        build([first, second])
        assert first.next_section() is second
        assert second.prev_section() is first

    def test_ends_of_the_range_return_none(self) -> None:
        first, second = Section(order=1), Section(order=2)
        build([first, second])
        assert second.next_section() is None
        assert first.prev_section() is None

    def test_prev_if_single_page_differs_by_mode(self) -> None:
        section = Section(order=3)
        build([section], multipage=True)
        assert section.prev_if_single_page() == 3

        other = Section(order=3)
        build([other], multipage=False)
        assert other.prev_if_single_page() == 2


class TestNavUrl:
    """
    Four axes: baking, multipage, search, and whether the section is first.
    """

    def url(self, include_anchor=True, order=1, **article_kwargs) -> str:
        section = Section(name="Chapter One", order=order)
        build([section], **article_kwargs)
        return section.nav_url(include_anchor)

    def test_live_single_page_is_a_fragment(self) -> None:
        assert self.url() == "#chapter-one"

    def test_live_single_page_with_search_is_absolute(self) -> None:
        assert self.url(search=True) == "/article/#chapter-one"

    def test_live_multipage_first_section_drops_the_anchor(self) -> None:
        assert self.url(multipage=True, order=1) == "/article/#"

    def test_live_multipage_later_section_uses_the_anchor(self) -> None:
        assert self.url(multipage=True, order=2) == "/article/chapter-one#chapter-one"

    def test_baked_single_page_is_a_fragment(self) -> None:
        assert self.url(baking=True) == "#chapter-one"

    def test_baked_single_page_with_search_points_at_index_html(self) -> None:
        assert self.url(baking=True, search=True) == "index.html#chapter-one"

    def test_baked_multipage_first_section_is_the_directory(self) -> None:
        assert self.url(baking=True, multipage=True, order=1) == "./#chapter-one"

    def test_baked_multipage_later_section_is_a_file(self) -> None:
        assert self.url(baking=True, multipage=True, order=2) == (
            "chapter-one.html#chapter-one"
        )

    def test_omitting_the_anchor_baked_multipage(self) -> None:
        assert self.url(False, 2, baking=True, multipage=True) == "chapter-one.html"
        assert self.url(False, 1, baking=True, multipage=True) == "./"

    def test_anchorless_nav_link_omits_the_anchor(self) -> None:
        section = Section(name="Chapter One", order=2)
        build([section], baking=True, multipage=True)
        assert section.anchorless_nav_link() == "chapter-one.html"


class TestGetGrafs:
    def section_with(self, grafs):
        section = Section(order=1, grafs=grafs)
        build([section])
        return section

    def test_normal_grafs_pass_through(self) -> None:
        section = self.section_with(
            [Graf(order=1, type=Graf.NORMAL, html="a"), Graf(order=2, type=Graf.NORMAL, html="b")]
        )
        assert len(list(section.get_grafs())) == 2

    def test_an_extended_run_collapses_into_one_graf(self) -> None:
        section = self.section_with(
            [
                Graf(order=1, type=Graf.EXTENDED_START, html="a"),
                Graf(order=2, type=Graf.EXTENDED_MIDDLE, html="b"),
                Graf(order=3, type=Graf.EXTENDED_END, html="c"),
            ]
        )
        result = list(section.get_grafs())
        assert len(result) == 1
        assert len(result[0].extra_grafs) == 2

    def test_a_complete_extended_graf_stands_alone(self) -> None:
        section = self.section_with([Graf(order=1, type=Graf.EXTENDED_COMPLETE, html="a")])
        assert len(list(section.get_grafs())) == 1

    def test_an_end_without_a_start_raises(self) -> None:
        section = self.section_with(
            [Graf(order=1, type=Graf.NORMAL, html="a"), Graf(order=2, type=Graf.EXTENDED_END, html="b")]
        )
        with pytest.raises(ValueError, match="paragraph end without start"):
            list(section.get_grafs())
