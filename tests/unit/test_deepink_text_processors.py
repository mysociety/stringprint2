"""
The str -> str stage of process_ink, plus the two soup helpers.

These run before markdown.markdown and are the most upgrade-sensitive part of
the parser, because markdown, bs4 and html5lib all move underneath them.
"""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup, NavigableString

from stringprint.tools.deepink import (
    get_classes,
    get_content,
    hide_footnote_refs,
    move_extended_close,
    quote_fix,
    return_footnote_refs,
)


def soup(html: str):
    return BeautifulSoup(html, features="html5lib")


class TestQuoteFix:
    @pytest.mark.parametrize(
        "given,expected",
        [
            ("“double”", '"double"'),
            ("it’s", "it's"),
            ("“mixed” and it’s", '"mixed" and it\'s'),
            ('already "straight"', 'already "straight"'),
            ("", ""),
        ],
    )
    def test_smart_quotes_become_straight(self, given: str, expected: str) -> None:
        assert quote_fix(given) == expected

    def test_falsy_input_is_returned_unchanged(self) -> None:
        assert quote_fix("") == ""
        assert quote_fix(None) is None


class TestMoveExtendedClose:
    def test_trailing_marker_moves_to_its_own_line(self) -> None:
        assert move_extended_close("some text]]") == "some text\n]]"

    def test_marker_already_alone_gains_a_blank_line(self) -> None:
        """
        A line that is just "]]" still matches, so it is split into an empty
        line plus the marker. Harmless downstream - markdown ignores the blank
        line - but it means the function is not idempotent.
        """
        assert move_extended_close("some text\n]]") == "some text\n\n]]"
        assert move_extended_close("]]") == "\n]]"

    def test_leading_whitespace_is_stripped_from_the_moved_line(self) -> None:
        assert move_extended_close("   some text]]") == "some text\n]]"

    def test_lines_without_the_marker_are_untouched(self) -> None:
        given = "first line\nsecond line"
        assert move_extended_close(given) == given

    def test_each_line_is_handled_independently(self) -> None:
        given = "one]]\ntwo\nthree]]"
        assert move_extended_close(given) == "one\n]]\ntwo\nthree\n]]"

    def test_a_blank_line_does_not_raise(self) -> None:
        assert move_extended_close("text\n\nmore") == "text\n\nmore"


class TestFootnoteRefHiding:
    """
    markdown.markdown is called with no extensions, so footnote syntax has to
    be hidden from it and put back afterwards.
    """

    def test_refs_are_hidden(self) -> None:
        assert hide_footnote_refs("a[^1] b") == "a!!footnotestandin!!1] b"

    def test_hiding_round_trips(self) -> None:
        given = "text[^1] more[^*] and[^named]"
        assert return_footnote_refs(hide_footnote_refs(given)) == given

    def test_definitions_are_hidden_too(self) -> None:
        given = "[^1]: the note"
        assert return_footnote_refs(hide_footnote_refs(given)) == given

    def test_text_without_refs_is_unchanged(self) -> None:
        assert hide_footnote_refs("no refs here") == "no refs here"

    def test_markdown_does_not_mangle_a_hidden_ref(self) -> None:
        import markdown

        hidden = hide_footnote_refs("a paragraph[^1] with a note")
        assert "[^" not in markdown.markdown(hidden)
        assert "!!footnotestandin!!" in markdown.markdown(hidden)


class TestGetClasses:
    def test_returns_the_class_list(self) -> None:
        tag = soup('<p class="one two">x</p>').find("p")
        assert get_classes(tag) == ["one", "two"]

    def test_returns_empty_when_absent(self) -> None:
        tag = soup("<p>x</p>").find("p")
        assert get_classes(tag) == []


class TestGetContent:
    def test_unwraps_an_extractable_tag(self) -> None:
        tag = soup("<p>plain text</p>").find("p")
        assert get_content(tag) == "plain text"

    def test_keeps_inline_markup_inside_an_extractable_tag(self) -> None:
        tag = soup("<p>a <em>b</em> c</p>").find("p")
        assert get_content(tag) == "a <em>b</em> c"

    def test_keeps_a_non_extractable_tag_whole(self) -> None:
        tag = soup("<div>inner</div>").find("div")
        assert get_content(tag) == "<div>inner</div>"

    def test_navigable_string_is_stringified(self) -> None:
        assert get_content(NavigableString("bare")) == "bare"

    def test_nested_extractable_tags_are_unwrapped_recursively(self) -> None:
        tag = soup("<blockquote><p>quoted</p></blockquote>").find("blockquote")
        assert get_content(tag) == "quoted"

    def test_empty_extractable_tag_is_stringified(self) -> None:
        tag = soup("<p></p>").find("p")
        assert get_content(tag) == "<p></p>"
