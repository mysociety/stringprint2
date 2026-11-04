"""
Footnotes and document-scoped numbering.
"""

from __future__ import annotations

import pytest

from stringprint.tools.deepink import Footnote, FootnoteRegistry, process_ink


class TestNumbering:
    def test_numbers_start_at_one_and_increment(self) -> None:
        registry = FootnoteRegistry()
        assert [Footnote(registry=registry).num for _ in range(3)] == [1, 2, 3]

    def test_section_num_starts_equal_to_num(self) -> None:
        note = Footnote()
        assert note.section_num == note.num

    def test_every_instance_registers_itself(self) -> None:
        registry = FootnoteRegistry()
        Footnote(registry=registry)
        Footnote(registry=registry)
        assert len(registry.notes) == 2


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


class TestCompilationIsolation:
    @pytest.mark.django_db
    def test_successive_documents_do_not_share_definitions(self, kitchen_sink) -> None:
        """
        A later document cannot fill an earlier document's unresolved reference.
        """
        first = kitchen_sink.content()
        process_ink(first, "# First\n\nMissing note.[^same]")
        unresolved = first.sections[0].grafs[0].footnotes[0]
        second = kitchen_sink.content()
        process_ink(second, "# Second\n\nNote.[^same]\n\n[^same]: Second document.")
        resolved = second.sections[0].grafs[0].footnotes[0]
        assert unresolved.content == ""
        assert resolved.content == "Second document."
        assert unresolved.num == resolved.num == 1

    def test_interleaved_registries_have_independent_numbering(self) -> None:
        """
        Interleaved compilations own their numbering independently.
        """
        first, second = FootnoteRegistry(), FootnoteRegistry()
        assert Footnote(registry=first).num == 1
        assert Footnote(registry=second).num == 1
        assert Footnote(registry=first).num == 2
