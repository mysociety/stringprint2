"""
Graf - the paragraph object. Everything here works on a detached instance.
"""

from __future__ import annotations

import pytest

from stringprint.tools.deepink import Graf


def graf(**kwargs) -> Graf:
    return Graf(**kwargs)


class TestAnchor:
    def test_uses_anchor_title_in_preference_to_title(self) -> None:
        assert graf(title="Title", anchor_title="Anchor Title").anchor() == (
            "anchor-title"
        )

    def test_falls_back_to_title(self) -> None:
        assert graf(title="Some Title").anchor() == "some-title"

    def test_punctuation_is_stripped(self) -> None:
        assert graf(title="What's this, then?").anchor() == "whats-this-then"

    def test_whitespace_becomes_hyphens(self) -> None:
        assert graf(title="a\tb\nc").anchor() == "a-b-c"

    def test_an_offset_is_appended(self) -> None:
        assert graf(title="Repeated", anchor_offset="2").anchor() == "repeated_2"

    def test_no_title_gives_an_empty_anchor(self) -> None:
        assert graf().anchor() == ""

    def test_non_breaking_space_escape_is_restored(self) -> None:
        assert graf(title="a%C2%A0b").anchor() == "ac2a0b"


class TestKeys:
    def make(self) -> Graf:
        return graf(
            parent_id=3,
            position_key=17,
            key="kkkkk",
            start_key="sssss",
            end_key="eeeee",
            letter_key="lllll",
            letter_seq="abc",
        )

    def test_combo_key_has_six_parts(self) -> None:
        assert self.make().combo_key() == "3.17.kkkkk.sssss.eeeee.lllll"

    def test_long_combo_key_adds_the_letter_sequence(self) -> None:
        assert self.make().long_combo_key() == "3.17.kkkkk.sssss.eeeee.lllll.abc"

    def test_the_long_key_extends_the_short_one(self) -> None:
        made = self.make()
        assert made.long_combo_key().startswith(made.combo_key())


class TestExtendedTypes:
    @pytest.mark.parametrize(
        "graf_type",
        [Graf.EXTENDED_START, Graf.EXTENDED_MIDDLE, Graf.EXTENDED_END, Graf.EXTENDED_COMPLETE],
    )
    def test_extended_types_report_extended(self, graf_type: str) -> None:
        assert graf(type=graf_type).extended() is True

    def test_normal_is_not_extended(self) -> None:
        assert graf(type=Graf.NORMAL).extended() is False

    def test_an_unset_type_is_not_extended(self) -> None:
        assert graf().extended() is False


class TestBlockStartAndEnd:
    def test_blockquote_after_a_non_block_starts_a_quote(self) -> None:
        assert graf(blockquote=True).block_start(prev_block=False) == "StartBlockQuote"

    def test_blockquote_after_a_block_does_not_restart(self) -> None:
        assert graf(blockquote=True).block_start(prev_block=True) is None

    @pytest.mark.parametrize("graf_type", [Graf.EXTENDED_START, Graf.EXTENDED_COMPLETE])
    def test_extended_openers_start_notes(self, graf_type: str) -> None:
        assert graf(type=graf_type).block_start(prev_block=False) == "StartNotes"

    def test_a_plain_graf_starts_nothing(self) -> None:
        assert graf(type=Graf.NORMAL).block_start(prev_block=False) is None

    def test_blockquote_before_a_non_block_ends_the_quote(self) -> None:
        assert graf(blockquote=True).block_end(next_block=False) is True

    def test_blockquote_before_a_block_does_not_end(self) -> None:
        assert graf(blockquote=True).block_end(next_block=True) is False

    @pytest.mark.parametrize("graf_type", [Graf.EXTENDED_END, Graf.EXTENDED_COMPLETE])
    def test_extended_closers_end_the_block(self, graf_type: str) -> None:
        assert graf(type=graf_type).block_end(next_block=True) is True

    def test_a_plain_graf_ends_nothing(self) -> None:
        assert graf(type=Graf.NORMAL).block_end(next_block=True) is False


class TestStartTagClassType:
    def test_blockquote_start_tag(self) -> None:
        assert graf(start_tag="StartBlockQuote").start_tag_class_type() == "blockquote"

    def test_notes_start_tag(self) -> None:
        assert graf(start_tag="StartNotes").start_tag_class_type() == "extended"

    def test_anything_else_is_empty(self) -> None:
        assert graf(start_tag="").start_tag_class_type() == ""

    def test_classes_marks_extended_rows(self) -> None:
        assert graf(start_tag="StartNotes").classes() == "extended-row"
        assert graf(start_tag="StartBlockQuote").classes() == ""


class TestContentHelpers:
    def test_has_content_follows_html(self) -> None:
        assert graf(html="text").has_content() is True
        assert graf(html="").has_content() is False

    def test_has_content_considers_extra_grafs(self) -> None:
        parent = graf(html="")
        parent.extra_grafs = [graf(html="child text")]
        assert parent.has_content() is True

    def test_self_and_extras_skips_empty_children(self) -> None:
        parent = graf(html="parent")
        parent.extra_grafs = [graf(html=""), graf(html="child")]
        assert [x.html for x in parent.self_and_extras()] == ["parent", "child"]

    def test_self_and_extras_keeps_title_only_grafs(self) -> None:
        parent = graf(html="")
        parent.extra_grafs = [graf(html="", title="A Title")]
        assert len(list(parent.self_and_extras())) == 1

    def test_escape_text_strips_brackets_and_newlines(self) -> None:
        assert graf(plain_txt="a [b] c\nd").escape_text() == "a b cd"

    def test_escape_text_drops_non_ascii(self) -> None:
        assert graf(plain_txt="café").escape_text() == "caf"


class TestElementTag:
    def test_an_asset_paragraph_becomes_a_div(self) -> None:
        assert graf(asset=1, h_name="p").get_element_tag() == "div"

    def test_a_plain_paragraph_keeps_its_tag(self) -> None:
        assert graf(asset=None, h_name="p").get_element_tag() == "p"

    def test_a_non_paragraph_with_an_asset_keeps_its_tag(self) -> None:
        assert graf(asset=1, h_name="blockquote").get_element_tag() == "blockquote"

