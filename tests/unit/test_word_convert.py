"""
The pure string fixups in the .docx -> markdown converter.

These run over mammoth's HTML output and are entirely self-contained, so they
are the cheapest real coverage in the codebase.
"""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from stringprint.tools.word_convert import (
    UniqueSlugify,
    fix_footnotes,
    fix_header,
    fix_markdown,
    fix_url,
    mammoth_adjust,
    markdown_table_contents,
    remove_supports,
)
from stringprint2.text_files import TextFile


class TestFixUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com",
            "http://example.com/path?q=1",
            "https://sub.example.co.uk/a/b",
            "http://localhost:8000/x",
            "http://127.0.0.1:8000/x",
        ],
    )
    def test_a_bare_url_becomes_a_labelled_link(self, url: str) -> None:
        assert fix_url(url) == "Link: [{0}]({0})".format(url)

    @pytest.mark.parametrize(
        "text", ["not a url", "example.com", "see https://example.com here", ""]
    )
    def test_anything_else_passes_through(self, text: str) -> None:
        assert fix_url(text) == text


class TestFixHeader:
    def test_level_is_preserved(self) -> None:
        assert fix_header("## A Heading") == "## A Heading"

    def test_all_caps_is_downcased_after_the_first_letter(self) -> None:
        assert fix_header("# SHOUTED HEADING") == "# Shouted heading"

    def test_mixed_case_is_left_alone(self) -> None:
        assert fix_header("# Mixed Case Heading") == "# Mixed Case Heading"

    def test_an_empty_heading_returns_empty(self) -> None:
        assert fix_header("###") == ""
        assert fix_header("#   ") == ""

    def test_hashes_anywhere_count_towards_the_level(self) -> None:
        # the level is every '#' in the line, not just the leading run
        assert fix_header("# a # b") == "## a  b"


class TestRemoveSupports:
    def test_is_currently_a_no_op(self) -> None:
        """
        The body of remove_supports is unreachable - it returns its argument on
        the first line. Pinned so the upgrade does not silently revive it.
        """
        given = '<li id="footnote-3"><p>text</p></li>'
        assert remove_supports(given) == given


class TestFixMarkdown:
    def test_text_without_markers_is_unchanged(self) -> None:
        assert fix_markdown("plain text") == "plain text"

    def test_whitespace_after_an_opening_marker_moves_before_it(self) -> None:
        assert fix_markdown("a__ bold__ b") == "a __bold__ b"

    def test_whitespace_before_a_closing_marker_moves_after_it(self) -> None:
        assert fix_markdown("a __bold __b") == "a __bold__ b"

    def test_already_correct_markers_are_untouched(self) -> None:
        assert fix_markdown("a __bold__ b") == "a __bold__ b"

    def test_a_marker_at_the_very_end_is_untouched(self) -> None:
        assert fix_markdown("trailing __") == "trailing __"


class TestMammothAdjust:
    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            ("__bold __", "__bold__ "),
            ("__ bold__", " __bold__"),
            ("_italic _", "_italic_ "),
            ("_ italic_", " _italic_"),
        ],
    )
    def test_malformed_emphasis_spacing_has_a_consistent_match_shape(
        self,
        source: str,
        expected: str,
    ) -> None:
        text_file = TextFile(text=f"# Heading\n{source}")

        mammoth_adjust(text_file, demote=False)

        assert expected in text_file.text


class TestFixFootnotes:
    def test_list_wrappers_are_dropped_and_refs_renumbered(self) -> None:
        block = (
            "<ol>"
            '<li id="footnote-0"><p>First note. '
            '<a href="#footnote-ref-0">↑</a></p></li>'
            '<li id="footnote-1"><p>Second note. '
            '<a href="#footnote-ref-1">↑</a></p></li>'
            "</ol>"
        )
        result = fix_footnotes(block)
        assert "<ol>" not in result and "</ol>" not in result
        # footnote numbering is one-based in the output
        assert result.startswith("[^1]: ")
        assert "[^2]: " in result

    def test_each_note_lands_on_its_own_line(self) -> None:
        block = (
            '<li id="footnote-0"><p>One</p></li>'
            '<li id="footnote-1"><p>Two</p></li>'
        )
        assert len(fix_footnotes(block).split("\n")) == 2


class TestMarkdownTableContents:
    def cell(self, html: str):
        return BeautifulSoup(html, "html.parser").find("td")

    def test_a_single_paragraph_cell_returns_its_markdown(self) -> None:
        assert markdown_table_contents(self.cell("<td><p>text</p></td>")) == "text"

    def test_an_empty_cell_returns_empty(self) -> None:
        assert markdown_table_contents(self.cell("<td></td>")) == ""

    def test_entities_are_replaced(self) -> None:
        result = markdown_table_contents(self.cell("<td><p>a&nbsp;b</p></td>"))
        assert "&nbsp;" not in result

    def test_multiple_paragraphs_switch_to_multi_line(self) -> None:
        result = markdown_table_contents(self.cell("<td><p>a</p><p>b</p></td>"))
        assert "a" in result and "b" in result
        assert result.endswith("\n\n")

    def test_multi_line_can_be_forced(self) -> None:
        result = markdown_table_contents(
            self.cell("<td><p>only</p></td>"), multi_line=True
        )
        assert result == "only\n\n"


class TestUniqueSlugify:
    def test_first_use_is_suffixed_with_one(self) -> None:
        assert UniqueSlugify().unique("Some Alt Text") == "some-alt-text-1"

    def test_repeats_increment(self) -> None:
        slugify = UniqueSlugify()
        assert [slugify.unique("Same") for _ in range(3)] == [
            "same-1",
            "same-2",
            "same-3",
        ]

    def test_only_the_first_twenty_characters_are_used(self) -> None:
        slugify = UniqueSlugify()
        first = slugify.unique("a" * 20 + "XXXX")
        second = slugify.unique("a" * 20 + "YYYY")
        assert first == "a" * 20 + "-1"
        assert second == "a" * 20 + "-2"

    def test_different_identifiers_are_independent(self) -> None:
        slugify = UniqueSlugify()
        assert slugify.unique("One") == "one-1"
        assert slugify.unique("Two") == "two-1"
