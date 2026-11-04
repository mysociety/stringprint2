"""Persistence and presentation contracts across the document module boundary."""

import json
from types import SimpleNamespace

from stringprint2.document_structure import Footnote, Graf, Section
from stringprint2.presentation.document import DocumentPresentation
from stringprint2.serialization import ObjectSerializer
from stringprint2.services.document_compilation import compile_document


def test_historical_imports_resolve_to_the_same_serialized_types():
    from stringprint.tools import deepink as historical
    from stringprint2.stringprint.tools import deepink

    for cls in (Section, Graf, Footnote):
        assert getattr(historical, cls.__name__) is cls
        assert getattr(deepink, cls.__name__) is cls
        assert ObjectSerializer.classes[cls.__name__] is cls


def test_stored_document_shape_round_trips_without_a_migration():
    stored = [
        {
            "_type": "Section",
            "_content": {
                "name": "Original",
                "order": 1,
                "anchor_offset": "",
                "grafs": [
                    {
                        "_type": "Graf",
                        "_content": {
                            "parent_id": 1,
                            "position_key": 77,
                            "key": "abcde",
                            "start_key": "fghij",
                            "end_key": "klmno",
                            "letter_key": "pqrst",
                            "letter_seq": "abc",
                            "footnotes": [
                                {
                                    "_type": "Footnote",
                                    "_content": {"content": "Stored note", "num": 1},
                                },
                            ],
                        },
                    },
                ],
            },
        }
    ]
    restored = ObjectSerializer.loads(json.dumps(stored))
    assert isinstance(restored[0], Section)
    paragraph = restored[0].grafs[0]
    assert isinstance(paragraph, Graf)
    assert isinstance(paragraph.footnotes[0], Footnote)
    assert paragraph.long_combo_key() == "1.77.abcde.fghij.klmno.pqrst.abc"
    assert json.loads(ObjectSerializer.dumps(restored)) == stored


def test_presentation_does_not_annotate_or_renumber_compiled_sections():
    compiled = compile_document(
        "# First\n\nOne.[^a]\n\n# Second\n\nTwo.[^b]\n\n[^a]: First note.\n\n[^b]: Second note.",
        seed=13,
        assets={},
    )
    before = ObjectSerializer.dumps(compiled.sections)
    version = SimpleNamespace(
        sections=compiled.sections, article=SimpleNamespace(multipage=True)
    )
    displayed = DocumentPresentation.for_version(version, ["second"])
    version.sections = displayed.sections
    assert [s.active_section for s in displayed.sections] == [False, True]
    second = list(displayed.sections[1].get_grafs())[0]
    assert second.footnotes[0].section_num == 1
    assert compiled.sections[1].grafs[0].footnotes[0].section_num == 2
    assert ObjectSerializer.dumps(compiled.sections) == before

    other = DocumentPresentation.for_version(
        SimpleNamespace(
            sections=compiled.sections, article=SimpleNamespace(multipage=False)
        ),
        display_first_section=True,
    )
    assert [s.active_section for s in other.sections] == [True, False]
    assert other.sections[0] is not displayed.sections[0]
