"""
stringprint.tools.preprocessing - the document preparation pipeline.

The text actions are pure str -> str. merge_pdfs uses PyMuPDF, which is why
the module is marked external.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from stringprint.tools.preprocessing import (
    SectionDelete,
    SectionMove,
    TextSnip,
    general_find_replace,
    merge_pdfs,
)

pytestmark = pytest.mark.external

DOCUMENT = "\n".join(
    [
        "Preamble line",
        "# Alpha",
        "alpha body",
        "# Beta",
        "beta body",
        "# Gamma",
        "gamma body",
    ]
)


def headings(text: str):
    return [line for line in text.split("\n") if line.startswith("# ")]


class TestSectionDelete:
    def test_the_named_section_is_removed(self) -> None:
        result = SectionDelete("# Beta")(DOCUMENT)
        assert headings(result) == ["# Alpha", "# Gamma"]

    def test_its_body_goes_with_it(self) -> None:
        assert "beta body" not in SectionDelete("# Beta")(DOCUMENT)

    def test_other_sections_are_untouched(self) -> None:
        result = SectionDelete("# Beta")(DOCUMENT)
        assert "alpha body" in result and "gamma body" in result

    def test_text_before_the_first_heading_survives(self) -> None:
        assert "Preamble line" in SectionDelete("# Beta")(DOCUMENT)

    def test_an_unknown_section_raises(self) -> None:
        with pytest.raises(ValueError):
            SectionDelete("# Missing")(DOCUMENT)


class TestSectionMove:
    def test_a_section_can_be_moved_after_another(self) -> None:
        result = SectionMove("# Alpha", after="# Gamma")(DOCUMENT)
        assert headings(result) == ["# Beta", "# Gamma", "# Alpha"]

    def test_a_section_can_be_moved_before_another(self) -> None:
        result = SectionMove("# Gamma", before="# Beta")(DOCUMENT)
        assert headings(result) == ["# Alpha", "# Gamma", "# Beta"]

    def test_the_body_travels_with_the_heading(self) -> None:
        result = SectionMove("# Alpha", after="# Gamma")(DOCUMENT)
        assert result.strip().endswith("alpha body")

    def test_neither_target_raises(self) -> None:
        with pytest.raises(ValueError, match="before"):
            SectionMove("# Alpha")

    def test_an_unknown_target_raises(self) -> None:
        with pytest.raises(ValueError):
            SectionMove("# Alpha", after="# Missing")(DOCUMENT)

    def test_only_the_second_definition_survives(self) -> None:
        """
        preprocessing.py declares SectionMove twice. The first is shadowed and
        dead - and would raise AttributeError on construction, because its
        __post_init__ reads self.before, which is not one of its fields.
        Pinned so the dead copy is not mistaken for the live one.
        """
        import dataclasses

        names = [field.name for field in dataclasses.fields(SectionMove)]
        assert names == ["section", "before", "after"]
        assert "to_delete" not in names


class TestTextSnip:
    def test_text_between_the_markers_is_removed(self) -> None:
        given = "keep this START drop this END keep that"
        # the snip takes the markers and everything between, leaving the
        # spaces that surrounded them
        assert TextSnip("START", "END")(given) == "keep this  keep that"

    def test_the_markers_go_too(self) -> None:
        result = TextSnip("START", "END")("a START b END c")
        assert "START" not in result and "END" not in result

    def test_the_end_marker_is_found_after_the_start(self) -> None:
        given = "END a START b END c"
        assert TextSnip("START", "END")(given) == "END a  c"


class TestGeneralFindReplace:
    def test_back_to_back_aside_markers_are_separated(self) -> None:
        assert general_find_replace == [("]][[", "]]\n\n[[")]

    def test_applying_it_splits_the_markers(self) -> None:
        text = "first aside]][[second aside"
        for old, new in general_find_replace:
            text = text.replace(old, new)
        assert text == "first aside]]\n\n[[second aside"


class TestMergePdfs:
    def test_the_cover_replaces_the_first_page(self, tmp_path, doc_folder) -> None:
        import fitz

        folder = doc_folder("kitchen-sink")
        output = tmp_path / "merged.pdf"
        merge_pdfs(folder / "cover.pdf", folder / "contents.pdf", output)

        assert output.exists()
        document = fitz.open(str(output))
        try:
            # cover page one, then the contents from page two onwards
            assert document.page_count == 3
            assert "cover" in document[0].get_text().lower()
            assert "page 1" in document[1].get_text()
            assert "page 0" not in document[1].get_text()
        finally:
            document.close()

    def test_a_later_start_page_drops_more_of_the_contents(
        self, tmp_path, doc_folder
    ) -> None:
        import fitz

        folder = doc_folder("kitchen-sink")
        output = tmp_path / "merged-skip.pdf"
        merge_pdfs(
            folder / "cover.pdf", folder / "contents.pdf", output, start_page=2
        )
        document = fitz.open(str(output))
        try:
            assert document.page_count == 2
            assert "page 2" in document[1].get_text()
        finally:
            document.close()
