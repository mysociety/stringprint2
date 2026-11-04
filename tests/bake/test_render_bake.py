"""
Article.render - the in-process bake that produces the published site.

Marked external: this is the only part of the suite that shells out to sass
and npx postcss, because Article.render reads self.compressed_files, which is
only populated by django-compressor's post_compress signal.

Web baking generates EPUB independently and leaves Kindle generation opt-in.
"""

from __future__ import annotations

import contextlib
import shutil
from pathlib import Path

import pytest

from contextlib import nullcontext
from unittest.mock import patch
from tests.conftest import FakeDriver

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.external,
    pytest.mark.slow,
    pytest.mark.needs_sass,
    pytest.mark.skipif(
        shutil.which("sass") is None or shutil.which("npx") is None,
        reason="needs sass and npx on PATH",
    ),
]


@contextlib.contextmanager
def compression_enabled():
    """
    Turn the real asset pipeline on for the duration of a bake.

    The output roots are deliberately left alone. django-compressor serves the
    app's own css and js out of COMPRESS_ROOT, which is the tracked
    stringprint2/static directory, so repointing it would make those files
    unfindable. Its build outputs go to static/CACHE and static/COMPILED,
    both of which are gitignored - the same places a normal run writes them.

    static_precompiler snapshots its configuration into module globals at
    import time, so its Django setting cannot be changed at runtime; the module
    attribute has to be swapped instead. It is read at call time, which is what
    makes that work.
    """
    import static_precompiler.settings

    saved_auto_compile = static_precompiler.settings.DISABLE_AUTO_COMPILE
    static_precompiler.settings.DISABLE_AUTO_COMPILE = False
    try:
        yield
    finally:
        static_precompiler.settings.DISABLE_AUTO_COMPILE = saved_auto_compile


def bake(article, destination: Path) -> Path:
    """
    Bake with real compilation and assert that caller state is unchanged.
    """
    from django.conf import settings

    names = ("SITE_ROOT", "DEBUG", "COMPRESS_ENABLED", "STATIC_URL", "MEDIA_URL")
    saved = {name: getattr(settings, name) for name in names}
    original = vars(article).copy()
    with compression_enabled():
        article.render(destination)
    assert {name: getattr(settings, name) for name in names} == saved
    assert vars(article) == original
    return destination


@pytest.fixture(scope="module")
def baked(tmp_path_factory, django_db_blocker, request) -> Path:
    """
    Bake once for the whole module - a full render runs sass, the compressor
    and every view, so it is far too slow to repeat per assertion.
    """
    article = request.getfixturevalue("kitchen_sink")
    driver = FakeDriver()
    with patch("stringprint2.services.paragraph_screenshots.paragraph_browser", lambda: nullcontext(driver)):
        with django_db_blocker.unblock():
            return bake(article, tmp_path_factory.mktemp("bake") / "baked")


class TestOutputFiles:
    @pytest.mark.parametrize(
        "name",
        [
            "index.html",
            "search.html",
            "plain.html",
            "toc.json",
            "search_content.js",
            "paragraph_map.json",
            "kitchen-sink.epub",
        ],
    )
    def test_the_expected_page_is_written(self, baked: Path, name: str) -> None:
        assert (baked / name).exists()

    def test_the_static_tree_is_created(self, baked: Path) -> None:
        for folder in ["static", "static/css", "static/js", "media"]:
            assert (baked / folder).is_dir(), folder

    def test_org_static_files_are_synced(self, baked: Path) -> None:
        assert (baked / "static" / "orgs" / "default").is_dir()

    def test_the_pdf_is_copied_alongside(self, baked: Path) -> None:
        assert (baked / "kitchen-sink.pdf").exists()

    def test_a_redirect_page_exists_per_paragraph_link(
        self, baked: Path, kitchen_sink
    ) -> None:
        links = list((baked / "l").glob("*.html"))
        assert links

    def test_media_files_are_copied(self, baked: Path) -> None:
        assert list((baked / "media").glob("*.png"))


class TestBakedContent:
    def test_the_index_holds_the_document(self, baked: Path) -> None:
        page = (baked / "index.html").read_text()
        assert "An ordinary opening paragraph" in page

    def test_the_org_template_override_is_applied(self, baked: Path) -> None:
        assert "ORG_TEMPLATE_OVERRIDE_MARKER" in (baked / "index.html").read_text()

    def test_baked_links_are_relative(self, baked: Path) -> None:
        page = (baked / "index.html").read_text()
        assert "http://127.0.0.1:8000" not in page

    def test_the_toc_is_valid_json(self, baked: Path) -> None:
        import json

        assert json.loads((baked / "toc.json").read_text())

    def test_compressed_css_is_emitted_and_copied(
        self, baked: Path, kitchen_sink
    ) -> None:
        assert list((baked / "static" / "CACHE").rglob("*.css"))
        assert list((baked / "static" / "CACHE").rglob("*.js"))


class TestMultipageBake:
    def test_a_page_is_written_per_section(
        self, tmp_path, multipage_doc, fake_chrome
    ) -> None:
        destination = bake(multipage_doc, tmp_path / "multipage")

        assert (destination / "index.html").exists()
        for section in multipage_doc.content().sections:
            if section.order == 1:
                continue
            assert (destination / "{0}.html".format(section.anchor())).exists()
        assert not (destination / "multipage-doc.epub").exists()
        assert 'type="epub"' not in (destination / "index.html").read_text()


class TestRenderIsolation:
    def test_failed_bake_leaves_settings_and_publication_unchanged(
        self, kitchen_sink, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        A failing build cannot change settings used by a live preview request.
        """
        from django.conf import settings
        from stringprint2.services import web_rendering

        names = ("SITE_ROOT", "DEBUG", "COMPRESS_ENABLED", "STATIC_URL")
        saved = {name: getattr(settings, name) for name in names}
        original = vars(kitchen_sink).copy()

        def fail(*args, **kwargs):
            assert {name: getattr(settings, name) for name in names} == saved
            raise RuntimeError("failed midway")

        monkeypatch.setattr(web_rendering, "write_baked_file", fail)
        monkeypatch.setattr(
            type(kitchen_sink), "export_paragraph_images", lambda *args, **kwargs: None
        )
        with pytest.raises(RuntimeError, match="failed midway"):
            kitchen_sink.render(tmp_path / "failed", epub=False)
        assert {name: getattr(settings, name) for name in names} == saved
        assert vars(kitchen_sink) == original

    def test_default_bake_advertises_only_generated_downloads(
        self, baked: Path
    ) -> None:
        """
        EPUB is available independently of the unconfigured Kindle generator.
        """
        page = (baked / "index.html").read_text()
        assert 'type="epub"' in page
        assert 'type="kindle"' not in page
        assert not (baked / "kitchen-sink.mobi").exists()

    def test_repeated_bakes_do_not_reuse_compressed_file_state(
        self, kitchen_sink, tmp_path: Path, fake_chrome
    ) -> None:
        """
        Consecutive renders of one instance collect complete fresh asset lists.
        """
        bake(kitchen_sink, tmp_path / "first")
        bake(kitchen_sink, tmp_path / "second")
        assert list((tmp_path / "second" / "static" / "CACHE").rglob("*.css"))

    def test_kindle_can_be_requested_without_epub_or_plain_text(
        self, kitchen_sink, tmp_path: Path, fake_chrome, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Each alternate output controls its own generated file and download link.
        """

        def generate(publication, destination: Path, use_temp: bool = False):
            (destination / f"{publication.slug}.mobi").write_bytes(b"mobi")

        monkeypatch.setattr(type(kitchen_sink), "create_kindle", generate)
        destination = tmp_path / "kindle-only"
        with compression_enabled():
            kitchen_sink.render(destination, kindle=True, epub=False, plain=False)
        page = (destination / "index.html").read_text()
        assert 'type="kindle"' in page
        assert 'type="epub"' not in page
        assert 'type="plain"' not in page
        assert (destination / "kitchen-sink.mobi").exists()
        assert not (destination / "kitchen-sink.epub").exists()
        assert not (destination / "plain.html").exists()


class TestBootstrap5PublicationOutput:
    """The final baked artefact, not just source templates, uses Bootstrap 5."""

    def test_baked_navigation_uses_bootstrap_5_markup(self, baked: Path) -> None:
        page = (baked / "index.html").read_text()

        assert "dropdown-menu-end" in page
        assert "data-menu-toggle" in page
        assert "me-auto" in page
        assert "ms-auto" in page
        for legacy in [
            "dropdown-menu-right",
            "data-toggle=",
            "data-target=",
            "mr-auto",
            "ml-auto",
        ]:
            assert legacy not in page

    def test_baked_search_uses_bootstrap_5_input_group(self, baked: Path) -> None:
        page = (baked / "search.html").read_text()

        assert 'class="input-group mb-3"' in page
        assert "input-group-append" not in page

    def test_baked_css_contains_selective_bootstrap_5_contract(
        self,
        baked: Path,
        kitchen_sink,
    ) -> None:
        stylesheets = [
            name.read_text() for name in (baked / "static" / "CACHE").rglob("*.css")
        ]
        css = "\n".join(stylesheets)

        assert "--bs-table-bg" in css
        assert ".dropdown-menu-end" in css
        assert ".fixed-top" in css
        assert "min-width:992px!important" in css.replace(" ", "")
        assert ".modal" not in css
        assert ".carousel" not in css
