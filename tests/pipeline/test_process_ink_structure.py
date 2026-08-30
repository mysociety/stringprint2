"""
process_ink - markdown into the Section/Graf tree.

The tree is what gets serialised into Version.sections, so this is the layer
where a markdown, bs4 or html5lib change would show up first.
"""

from __future__ import annotations

import pytest

from stringprint.tools.deepink import Graf

pytestmark = pytest.mark.django_db


@pytest.fixture
def sections(kitchen_sink):
    return kitchen_sink.content().sections


def section_named(sections, name):
    for section in sections:
        if section.name == name:
            return section
    raise AssertionError("no section named {0!r}".format(name))


def grafs(sections):
    for section in sections:
        for graf in section.grafs:
            yield graf


class TestSectionSplitting:
    def test_one_section_per_h1(self, sections) -> None:
        assert [s.name for s in sections] == [
            "Opening Section",
            "Assets and Markers",
            "Notes and Asides",
            "Footnotes",
            "Duplicate Headings",
        ]

    def test_sections_are_ordered_from_one(self, sections) -> None:
        assert [s.order for s in sections] == [1, 2, 3, 4, 5]

    def test_anchors_are_slugified_names(self, sections) -> None:
        assert [s.anchor() for s in sections][:2] == [
            "opening-section",
            "assets-and-markers",
        ]

    def test_grafs_are_numbered_across_the_whole_document(self, sections) -> None:
        orders = [graf.order for graf in grafs(sections)]
        assert orders == sorted(orders)
        assert orders[0] == 1

    def test_a_document_with_one_heading_gets_one_section(self, minimal_doc) -> None:
        assert len(minimal_doc.content().sections) == 1


class TestTitles:
    def test_a_subheading_titles_the_following_graf(self, sections) -> None:
        section = section_named(sections, "Opening Section")
        titled = [g for g in section.grafs if g.title]
        assert "A Titled Paragraph" in [g.title for g in titled]

    def test_the_header_level_is_recorded(self, sections) -> None:
        levels = {g.title: g.header_level for g in grafs(sections) if g.title}
        assert levels["A Titled Paragraph"] == 2
        assert levels["A Third Level Title"] == 3
        assert levels["A Fourth Level Straight After"] == 4

    def test_two_headings_in_a_row_emit_a_title_only_graf(self, sections) -> None:
        section = section_named(sections, "Opening Section")
        third = [g for g in section.grafs if g.title == "A Third Level Title"][0]
        assert third.html == ""

    def test_anchor_titles_combine_section_and_heading(self, sections) -> None:
        section = section_named(sections, "Duplicate Headings")
        assert section.grafs[0].anchor_title == "Duplicate Headings Repeated Heading"


class TestAnchorDeduplication:
    def test_repeated_headings_get_numeric_suffixes(self, sections) -> None:
        section = section_named(sections, "Duplicate Headings")
        assert [g.anchor() for g in section.grafs] == [
            "duplicate-headings-repeated-heading",
            "duplicate-headings-repeated-heading_1",
            "duplicate-headings-repeated-heading_2",
        ]

    def test_repeated_h1_names_are_deduplicated_too(self, multipage_doc) -> None:
        anchors = [s.anchor() for s in multipage_doc.content().sections]
        assert anchors == ["first-chapter", "second-chapter", "first-chapter_1"]


class TestBlockquotes:
    def test_quote_blocks_separated_by_a_blank_line_merge(self, sections) -> None:
        """
        Markdown folds adjacent '>' blocks into a single blockquote element, so
        this is one graf carrying two paragraphs, not two grafs.
        """
        section = section_named(sections, "Opening Section")
        quotes = [g for g in section.grafs if g.blockquote]
        merged = [g for g in quotes if "single blockquote element" in g.html]
        assert len(merged) == 1
        assert merged[0].html.count("<p>") == 2

    def test_blocks_separated_by_a_comment_stay_distinct(self, sections) -> None:
        section = section_named(sections, "Opening Section")
        adjacent = [g for g in section.grafs if "genuinely adjacent" in (g.html or "")]
        assert len(adjacent) == 2

    def test_adjacent_quotes_open_once_and_close_once(self, sections) -> None:
        section = section_named(sections, "Opening Section")
        adjacent = [g for g in section.grafs if "genuinely adjacent" in (g.html or "")]
        first, second = adjacent
        assert first.block_start(prev_block=False) == "StartBlockQuote"
        assert first.block_end(next_block=True) is False
        assert second.block_start(prev_block=True) is None
        assert second.block_end(next_block=False) is True

    def test_plain_paragraphs_are_not_marked_as_quotes(self, sections) -> None:
        section = section_named(sections, "Opening Section")
        assert any(g.blockquote is False for g in section.grafs)


class TestExtendedBlocks:
    def test_the_full_run_of_types_appears(self, sections) -> None:
        types = {g.type for g in grafs(sections)}
        assert {
            Graf.NORMAL,
            Graf.EXTENDED_START,
            Graf.EXTENDED_MIDDLE,
            Graf.EXTENDED_END,
            Graf.EXTENDED_COMPLETE,
        } <= types

    def test_a_one_paragraph_aside_is_complete(self, sections) -> None:
        section = section_named(sections, "Notes and Asides")
        complete = [g for g in section.grafs if g.type == Graf.EXTENDED_COMPLETE]
        assert any("complete in itself" in g.html for g in complete)

    def test_a_multi_paragraph_aside_opens_and_closes(self, sections) -> None:
        section = section_named(sections, "Notes and Asides")
        types = [g.type for g in section.grafs]
        start = types.index(Graf.EXTENDED_START)
        assert Graf.EXTENDED_MIDDLE in types[start:]
        assert Graf.EXTENDED_END in types[start:]

    def test_every_start_is_matched_by_an_end(self, sections) -> None:
        section = section_named(sections, "Notes and Asides")
        types = [g.type for g in section.grafs]
        assert types.count(Graf.EXTENDED_START) == types.count(Graf.EXTENDED_END)

    def test_a_lone_opening_marker_still_opens_a_block(self, sections) -> None:
        section = section_named(sections, "Notes and Asides")
        assert any(
            "opened by a marker on its own line" in (g.html or "") and g.extended()
            for g in section.grafs
        )

    def test_a_trailing_close_marker_is_normalised(self, sections) -> None:
        section = section_named(sections, "Notes and Asides")
        assert any(
            "closed on the same line" in (g.html or "") and g.extended()
            for g in section.grafs
        )

    def test_asides_set_has_notes(self, kitchen_sink, minimal_doc) -> None:
        assert kitchen_sink.content().has_notes is True
        assert minimal_doc.content().has_notes is False


class TestAssets:
    def test_an_asset_reference_attaches_the_asset_id(
        self, sections, kitchen_sink
    ) -> None:
        by_slug = {a.slug: a.id for a in kitchen_sink.assets.all()}
        referenced = {g.asset for g in grafs(sections) if g.asset}
        assert by_slug["image-one"] in referenced
        assert by_slug["table-one"] in referenced
        assert by_slug["html-one"] in referenced

    def test_a_missing_asset_leaves_a_marker(self, sections) -> None:
        assert any("ASSET MISSING" in (g.html or "") for g in grafs(sections))

    def test_referenced_assets_are_marked_active(self, kitchen_sink) -> None:
        active = set(kitchen_sink.assets.filter(active=True).values_list("slug", flat=True))
        assert {"image-one", "table-one", "html-one"} <= active

    def test_an_unreferenced_asset_is_left_inactive(self, kitchen_sink) -> None:
        """
        process_ink deactivates every asset up front and reactivates the ones
        the text actually uses. image-three is declared but never referenced.
        """
        assert kitchen_sink.assets.get(slug="image-three").active is False

    def test_a_header_asset_is_recorded_on_the_section(
        self, sections, kitchen_sink
    ) -> None:
        section = section_named(sections, "Assets and Markers")
        expected = kitchen_sink.assets.get(slug="image-two").id
        assert section.header_asset == expected

    def test_used_assets_reports_both_kinds(self, sections) -> None:
        section = section_named(sections, "Assets and Markers")
        assert len(section.used_assets()) >= 4


class TestMarkers:
    def test_a_tag_is_recorded_on_the_graf(self, sections) -> None:
        tagged = [g for g in grafs(sections) if g.tag]
        assert [g.tag for g in tagged] == ["mytag"]

    def test_tags_are_indexed_onto_the_section(self, sections) -> None:
        section = section_named(sections, "Assets and Markers")
        assert section.tagged == {"mytag": section.order}

    def test_a_paragraph_marker_is_recorded(self, sections) -> None:
        assert [g.para_tag for g in grafs(sections) if g.para_tag] == ["mypara"]

    def test_a_page_marker_is_recorded(self, sections) -> None:
        assert [g.page_tag for g in grafs(sections) if g.page_tag] == ["12"]

    def test_page_markers_work_mid_sentence(self, legacy_doc) -> None:
        pages = [
            g.page_tag
            for section in legacy_doc.content().sections
            for g in section.grafs
            if g.page_tag
        ]
        assert pages == ["12", "13"]

    def test_markers_are_stripped_from_the_rendered_html(self, sections) -> None:
        for graf in grafs(sections):
            assert "[tag:" not in (graf.html or "")
            assert "[para:" not in (graf.html or "")
            assert "[page:" not in (graf.html or "")


class TestCatchUp:
    def test_the_catchup_line_is_attached_to_the_section(self, sections) -> None:
        section = section_named(sections, "Assets and Markers")
        assert section.catch_up.startswith("A short catchup line")

    def test_the_marker_does_not_become_a_graf(self, sections) -> None:
        for graf in grafs(sections):
            assert "[catchup:" not in (graf.html or "")


class TestKeys:
    def test_position_keys_count_up_with_seed_minus_one(self, sections) -> None:
        """
        A seed of -1 makes RandomAssignment hand out 1, 2, 3... in document
        order. Not every drawn number survives onto a stored graf - some are
        consumed by grafs that are later merged or dropped - so the sequence
        can skip. What matters for citation stability is that keys are unique
        and strictly increasing.
        """
        keys = [g.position_key for g in grafs(sections) if g.position_key]
        assert keys[0] == 1
        assert keys == sorted(keys)
        assert len(set(keys)) == len(keys)

    def test_title_only_grafs_have_no_position_key(self, sections) -> None:
        title_only = [g for g in grafs(sections) if g.title and not g.html]
        assert title_only
        assert all(g.position_key == 0 for g in title_only)

    def test_combo_keys_are_unique(self, sections) -> None:
        keys = [g.long_combo_key() for g in grafs(sections)]
        assert len(set(keys)) == len(keys)

    def test_a_legacy_seed_gives_non_sequential_keys(self, legacy_doc) -> None:
        keys = [
            g.position_key
            for section in legacy_doc.content().sections
            for g in section.grafs
        ]
        assert keys != list(range(1, len(keys) + 1))
        assert len(set(keys)) == len(keys)
