"""
Version paragraph links - the stable per-paragraph anchors kept in
_paragraphs.yaml so citation URLs survive edits.

This is the one file the app writes back into the document source, which is
why the fixture tree is copied to a temporary directory for the test session.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

pytestmark = pytest.mark.django_db

STALE_KEYS = [
    "1.1.aaaaa.bbbbb.ccccc.ddddd.ldcppmiwtt",
    "1.2.eeeee.fffff.ggggg.hhhhh.aspoptoto",
    "2.1.iiiii.jjjjj.kkkkk.lllll.tfsctd",
]


def read_yaml(path):
    with open(str(path)) as file_handle:
        return YAML(typ="safe").load(file_handle)


@pytest.fixture
def isolated_source(tmp_path, settings):
    """
    A private copy of the *committed* document source.

    _paragraphs.yaml is shared session state that processing rewrites, so a
    test asserting on the file as it ships has to work from its own pristine
    copy - taking one from the session tree would still depend on whether a
    processing test happened to run first.
    """
    import shutil

    import stringprint_test_env

    destination = tmp_path / "doc_source"
    shutil.copytree(
        str(stringprint_test_env.FIXTURES / "doc_source"), str(destination)
    )
    settings.ORGS = dict(settings.ORGS)
    settings.ORGS["default"] = dict(settings.ORGS["default"])
    settings.ORGS["default"]["storage_dir"] = str(destination)
    return destination


class TestLoadAndSave:
    def test_an_existing_file_is_read(self, isolated_source, load_doc) -> None:
        version = load_doc("legacy-doc").content()
        version.load_paragraph_links()
        assert len(version.paragraph_links) == 3

    def test_a_missing_file_gives_an_empty_list(
        self, isolated_source, load_doc
    ) -> None:
        assert not (
            isolated_source / "_docs" / "minimal-doc" / "_paragraphs.yaml"
        ).exists()
        version = load_doc("minimal-doc").content()
        version.load_paragraph_links()
        assert version.paragraph_links == []

    def test_saving_round_trips(self, isolated_source, load_doc) -> None:
        version = load_doc("minimal-doc").content()
        version.paragraph_links = [{"a.b.c.d.e.f.g": True}]
        version.save_paragraph_links()

        written = read_yaml(
            isolated_source / "_docs" / "minimal-doc" / "_paragraphs.yaml"
        )
        assert written == [{"a.b.c.d.e.f.g": True}]

    def test_paragraph_lookup_flattens_the_list(
        self, isolated_source, load_doc
    ) -> None:
        version = load_doc("legacy-doc").content()
        version.load_paragraph_links()
        lookup = version.paragraph_lookup()
        assert set(lookup) == set(STALE_KEYS)
        assert all(value is True for value in lookup.values())

    def test_paragraph_lookup_skips_empty_entries(self, load_doc) -> None:
        version = load_doc("minimal-doc").content()
        version.paragraph_links = [None, {"a": True}]
        assert version.paragraph_lookup() == {"a": True}


class TestSourceFromRender:
    def test_previously_rendered_links_are_discovered(self, process_doc) -> None:
        version = process_doc("legacy-doc").content()
        found = version.source_paragraph_links_from_render()
        assert sorted(found) == sorted(key.rsplit(".", 1)[0] for key in STALE_KEYS)

    def test_a_document_never_rendered_yields_nothing(self, process_doc) -> None:
        version = process_doc("minimal-doc").content()
        assert version.source_paragraph_links_from_render() == []


class TestUpdateParagraphLinks:
    @pytest.fixture(scope="class")
    def updated(self, process_doc, doc_folder):
        # processing already ran update_paragraph_links
        version = process_doc("legacy-doc").content()
        return read_yaml(doc_folder("legacy-doc") / "_paragraphs.yaml"), version

    def test_the_file_is_rewritten_on_process(self, updated) -> None:
        written, _ = updated
        assert written, "processing should have written paragraph links"

    def test_every_current_graf_is_recorded(self, updated) -> None:
        written, version = updated
        keys = set()
        for entry in written:
            keys.update(entry.keys())
        for section in version.sections:
            for graf in section.grafs:
                assert graf.long_combo_key() in keys

    def test_current_grafs_are_marked_live(self, updated) -> None:
        written, version = updated
        lookup = {}
        for entry in written:
            lookup.update(entry)
        first = version.sections[0].grafs[0]
        assert lookup[first.long_combo_key()] is True

    def test_stale_keys_are_kept_rather_than_dropped(self, updated) -> None:
        """
        Old links have to survive, otherwise previously published citation URLs
        would 404. They are kept with a value of None (no mapping) or a string
        (re-anchored onto a current paragraph).
        """
        written, _ = updated
        keys = set()
        for entry in written:
            keys.update(entry.keys())
        assert set(STALE_KEYS) & keys

    def test_stale_keys_are_not_marked_live(self, updated) -> None:
        written, _ = updated
        lookup = {}
        for entry in written:
            lookup.update(entry)
        for key in STALE_KEYS:
            assert lookup[key] is not True

    def test_a_stale_key_is_re_anchored_onto_a_current_paragraph(
        self, updated
    ) -> None:
        """
        anchor_orphans fuzzy-matches an old key against the current paragraphs
        so an existing citation URL keeps resolving. A re-anchored entry holds
        the replacement key as its value rather than True or None.
        """
        written, version = updated
        lookup = {}
        for entry in written:
            lookup.update(entry)

        current = {
            graf.long_combo_key()
            for section in version.sections
            for graf in section.grafs
        }
        redirected = [
            value
            for key, value in lookup.items()
            if key in STALE_KEYS and isinstance(value, str)
        ]
        assert redirected, "no stale key was re-anchored"
        assert all(value in current for value in redirected)
