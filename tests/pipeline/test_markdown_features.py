"""
One test per markdown construct the parser supports.

These are deliberately fine-grained: with no golden files in the suite, this
is where a change in markdown, bs4 or html5lib has to be caught, and a
per-construct failure says which construct broke.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def html(kitchen_sink):
    """All rendered graf html for the kitchen sink document, joined."""
    return "\n".join(
        graf.html or ""
        for section in kitchen_sink.content().sections
        for graf in section.grafs
    )


@pytest.fixture
def graf_with(kitchen_sink):
    def find(fragment: str):
        matches = [
            graf
            for section in kitchen_sink.content().sections
            for graf in section.grafs
            if fragment in (graf.html or "")
        ]
        assert matches, "no graf containing {0!r}".format(fragment)
        return matches[0]

    return find


class TestLists:
    def test_an_unordered_list_is_one_graf(self, graf_with) -> None:
        graf = graf_with("first list item")
        assert graf.h_name == "ul"
        assert graf.html.count("<li>") == 2

    def test_an_ordered_list_is_one_graf(self, graf_with) -> None:
        graf = graf_with("first numbered item")
        assert graf.h_name == "ol"
        assert graf.html.count("<li>") == 2


class TestRawHtml:
    def test_a_raw_table_survives(self, graf_with) -> None:
        graf = graf_with("Heading A")
        assert "<td>" in graf.html
        assert "Cell one" in graf.html


class TestQuotes:
    def test_double_quoted_spans_become_quote_markup(self, html: str) -> None:
        assert 'class="quote"' in html
        assert "a double quoted span" in html

    def test_the_double_quote_markers_are_consumed(self, graf_with) -> None:
        graf = graf_with("a double quoted span")
        assert '""' not in graf.html

    def test_an_empty_html_attribute_is_not_treated_as_a_quote(
        self, graf_with
    ) -> None:
        """
        The `=""` of an empty HTML attribute would otherwise look like a quote
        marker, so it is protected by a placeholder and restored afterwards.
        """
        graf = graf_with("carrying an empty value")
        assert 'data-empty=""' in graf.html
        assert "%EMPTYHTMLTAG%" not in graf.html

    def test_smart_quotes_are_straightened(self, html: str) -> None:
        assert "“" not in html
        assert "”" not in html
        assert "’" not in html
        assert '"curly double"' in html


class TestLinks:
    def test_an_internal_anchor_link_is_kept(self, graf_with) -> None:
        graf = graf_with("the opening section")
        assert 'href="#opening-section"' in graf.html

    def test_a_footnote_link_is_rendered(self, kitchen_sink) -> None:
        notes = [
            note
            for section in kitchen_sink.content().sections
            for graf in section.grafs
            for note in graf.footnotes
        ]
        with_link = [n for n in notes if "<a " in (n.content or "")]
        assert with_link


class TestFootnotes:
    @pytest.fixture
    def notes(self, kitchen_sink):
        return [
            note
            for section in kitchen_sink.content().sections
            for graf in section.grafs
            for note in graf.footnotes
        ]

    def test_every_reference_produces_a_note(self, notes) -> None:
        assert len(notes) == 5

    def test_notes_are_numbered_in_document_order(self, notes) -> None:
        assert [note.num for note in notes] == [1, 2, 3, 4, 5]

    def test_a_numbered_definition_is_attached(self, notes) -> None:
        first = [n for n in notes if n.local_ref == "[^1]"][0]
        assert "The first footnote" in first.content

    def test_a_starred_reference_is_supported(self, notes) -> None:
        starred = [n for n in notes if n.local_ref == "[^*]"][0]
        assert "referenced by a star" in starred.content

    def test_a_labelled_definition_splits_off_the_label(self, notes) -> None:
        labelled = [n for n in notes if n.named_reference][0]
        assert labelled.named_reference == "Labelled Footnote"
        assert labelled.content.startswith("The content of a footnote")

    def test_an_alphabetic_reference_never_finds_its_definition(self, notes) -> None:
        """
        Known defect: connect_to_footnote matches definitions with the regex
        \\[\\^[0-9\\*]+\\]\\:, which accepts digits and stars but no letters. A
        named reference such as [^scotedit] is therefore parsed as a reference
        but its definition line is never matched, leaving the note empty.
        At least one production document uses this syntax.

        Pinned rather than fixed; see docs/feature-inventory.md.
        """
        named = [n for n in notes if n.local_ref == "[^scotedit]"][0]
        assert named.content == ""

    def test_references_are_removed_from_the_paragraph_text(self, html: str) -> None:
        assert "[^" not in html
        assert "!!footnotestandin!!" not in html

    def test_definition_lines_do_not_become_grafs(self, kitchen_sink) -> None:
        for section in kitchen_sink.content().sections:
            for graf in section.grafs:
                assert not (graf.html or "").startswith("[^")


class TestAsides:
    def test_the_aside_markers_are_consumed(self, html: str) -> None:
        assert "[[" not in html
        assert "]]" not in html

    def test_aside_content_is_preserved(self, html: str) -> None:
        assert "A single paragraph aside" in html
        assert "The middle paragraph of the aside." in html


class TestAssetReferences:
    def test_asset_markers_are_replaced(self, html: str) -> None:
        assert "[asset:" not in html

    def test_an_asset_marker_is_replaced_by_the_asset_id(
        self, kitchen_sink
    ) -> None:
        """
        The marker is substituted with the asset's primary key, which becomes
        both graf.asset and the whole body of the graf - the template renders
        the asset from the id rather than from the text.
        """
        asset_grafs = [
            graf
            for section in kitchen_sink.content().sections
            for graf in section.grafs
            if graf.asset
        ]
        assert asset_grafs
        for graf in asset_grafs:
            assert graf.html.strip() == str(graf.asset)

    def test_a_header_asset_marker_is_consumed(self, html: str) -> None:
        assert "[header-asset:" not in html
