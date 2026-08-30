"""
Footnote, including its class-level mutable state.
"""

from __future__ import annotations

import pytest

from stringprint.tools.deepink import Footnote


@pytest.fixture(autouse=True)
def clean_registry():
    Footnote.note_count = 0
    Footnote.all = []
    yield
    Footnote.note_count = 0
    Footnote.all = []


class TestNumbering:
    def test_numbers_start_at_one_and_increment(self) -> None:
        assert [Footnote().num for _ in range(3)] == [1, 2, 3]

    def test_section_num_starts_equal_to_num(self) -> None:
        note = Footnote()
        assert note.section_num == note.num

    def test_every_instance_registers_itself(self) -> None:
        Footnote()
        Footnote()
        assert len(Footnote.all) == 2


class TestNamedReferences:
    def test_a_plain_ref_has_no_name(self) -> None:
        note = Footnote(local_ref="[^1]")
        assert note.local_ref == "[^1]"
        assert note.named_reference is None

    def test_a_name_in_the_ref_is_split_off(self) -> None:
        note = Footnote(local_ref="[^1||Some Name]")
        assert note.local_ref == "[^1]"
        assert note.named_reference == "Some Name"

    def test_a_name_in_the_content_is_split_off(self) -> None:
        note = Footnote(content="Some Name||the actual content")
        assert note.named_reference == "Some Name"
        assert note.content == "the actual content"

    def test_set_content_without_a_name_sets_content_only(self) -> None:
        note = Footnote()
        note.set_content("just content")
        assert note.content == "just content"
        assert note.named_reference is None


class TestFormatting:
    def test_numbered_refs_render_as_superscript(self) -> None:
        note = Footnote(local_ref="[^1]")
        result = note.format(order=7)
        assert "<sup>" in result
        assert 'id="7"' in result
        assert ">1<" in result

    def test_named_refs_render_without_superscript(self) -> None:
        note = Footnote(local_ref="[^1||A Name]")
        result = note.format(order=7)
        assert "<sup>" not in result
        assert "A Name" in result

    def test_kindle_numbered_format(self) -> None:
        note = Footnote(local_ref="[^1]")
        result = note.format_kindle()
        assert 'epub:type="noteref"' in result
        assert "<sup>1</sup>" in result

    def test_kindle_named_format(self) -> None:
        note = Footnote(local_ref="[^1||A Name]")
        result = note.format_kindle()
        assert "A Name" in result
        assert "<sup>" not in result

    def test_safe_content_is_marked_safe(self) -> None:
        from django.utils.safestring import SafeData

        assert isinstance(Footnote(content="<b>x</b>").safe_content(), SafeData)


class TestKindleContent:
    def test_plain_content_passes_through(self) -> None:
        assert Footnote(content="no links").kindle_content() == "no links"

    def test_a_single_link_is_flattened_and_appended(self) -> None:
        note = Footnote(content='see <a href="https://example.invalid">here</a>')
        result = note.kindle_content()
        assert "link: " in result
        assert "https://example.invalid" in result

    def test_ampersands_are_escaped(self) -> None:
        assert "&amp;" in Footnote(content="a & b").kindle_content()


class TestGlobalState:
    def test_all_is_shared_across_instances(self) -> None:
        """
        Footnote.all and note_count are class attributes. process_ink resets
        note_count on every run but never resets all, so the registry grows for
        the life of the process.

        That matters because connect_to_footnote scans the registry for an
        entry with empty content and a matching local_ref - so an unresolved
        footnote from one document can capture a later document's definition.
        The test suite works around it with an autouse fixture in
        tests/conftest.py. Pinned rather than fixed; see the inventory.
        """
        first = Footnote(local_ref="[^1]")
        assert Footnote.all == [first]

        second = Footnote(local_ref="[^2]")
        assert Footnote.all == [first, second]
        assert second.num == 2
