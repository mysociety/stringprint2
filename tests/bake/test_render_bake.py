"""
Article.render - the in-process bake that produces the published site.

Marked external: this is the only part of the suite that shells out to sass
and npx postcss, because Article.render reads self.compressed_files, which is
only populated by django-compressor's post_compress signal.

kindle=False throughout: kindlegen is not available and create_kindle is out
of scope. Article.render defaults kindle=True, so this is not optional.
"""

from __future__ import annotations

import contextlib
import shutil
from pathlib import Path

import pytest

from stringprint.models import Chrome
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
    from django.conf import settings

    names = [
        "COMPRESS_ENABLED",
        "MEDIA_URL",
        "MEDIA_ROOT",
        "STATIC_URL",
        "COMPRESS_URL",
        "SITE_ROOT",
        "DEBUG",
    ]
    saved = {name: getattr(settings, name) for name in names}
    saved_auto_compile = static_precompiler.settings.DISABLE_AUTO_COMPILE

    settings.COMPRESS_ENABLED = True
    static_precompiler.settings.DISABLE_AUTO_COMPILE = False
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(settings, name, value)
        static_precompiler.settings.DISABLE_AUTO_COMPILE = saved_auto_compile


def bake(article, destination: Path) -> Path:
    # compressed_files accumulates across renders, and render() strips the
    # COMPRESS_URL prefix from every entry each time - so a second render over
    # the same instance would strip already-stripped names and lose the files.
    article.compressed_files = []
    was_baking = getattr(article, "baking", False)
    try:
        with compression_enabled():
            # no url argument: render() would otherwise overwrite
            # production_url on the article and save it, which leaks onto the
            # shared session fixture. The CLI does not pass one either.
            article.render(destination, kindle=False)
    finally:
        # render() sets baking on the instance and never clears it. It is not a
        # model field, so nothing else puts it back, and it silently changes
        # what url() and social_url() return for every later test.
        article.baking = was_baking
    return destination


@pytest.fixture(scope="module")
def baked(tmp_path_factory, django_db_blocker, request) -> Path:
    """
    Bake once for the whole module - a full render runs sass, the compressor
    and every view, so it is far too slow to repeat per assertion.
    """
    article = request.getfixturevalue("kitchen_sink")
    driver = FakeDriver()
    Chrome.page = None
    original = Chrome.get_page
    Chrome.get_page = classmethod(lambda cls: driver)
    try:
        with django_db_blocker.unblock():
            return bake(article, tmp_path_factory.mktemp("bake") / "baked")
    finally:
        Chrome.get_page = original
        Chrome.page = None


class TestOutputFiles:
    @pytest.mark.parametrize(
        "name",
        [
            "index.html",
            "search.html",
            "plain.html",
            "toc.json",
            "tipuesearch_content.js",
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
        assert kitchen_sink.compressed_files, "post_compress signal never fired"
        for name in kitchen_sink.compressed_files:
            assert (baked / "static" / name).exists(), name


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


class TestSettingsRestoration:
    def test_settings_are_restored_after_a_bake(self, baked) -> None:
        """
        Article.render sets SITE_ROOT, DEBUG and COMPRESS_ENABLED on the
        settings module and never puts them back. compression_enabled and
        the autouse fixture in tests/conftest.py between them undo that -
        this checks the undoing actually happens, so neither is quietly
        dropped.
        """
        from django.conf import settings as live

        assert live.SITE_ROOT != "https://example.invalid/html/kitchen-sink/"
        assert live.COMPRESS_ENABLED is False
