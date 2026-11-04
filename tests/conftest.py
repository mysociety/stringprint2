"""
Shared fixtures.

Two things routinely catch people out in this codebase:

* Section.nav_url and Graf.display read article.search and article.baking,
  which are not model fields - the views inject them through
  article_settings_override. A bare Article() has to set them by hand.
* Section.get_grafs memoises stored_grafs onto the instance, so a test
  asserting on the serialised tree should re-read the Version from the
  database rather than reuse a session-scoped in-memory object.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Callable, Dict

import pytest
from django.conf import settings

from stringprint_test_env import DOC_SOURCE, MEDIA_ROOT


@pytest.fixture(scope="session")
def doc_source() -> Path:
    """The writable copy of the fixture document source."""
    return DOC_SOURCE


@pytest.fixture(scope="session")
def media_root() -> Path:
    return MEDIA_ROOT


@pytest.fixture(scope="session")
def doc_folder(doc_source: Path) -> Callable[[str], Path]:
    def get(slug: str) -> Path:
        return Path(doc_source, "_docs", slug)

    return get


@pytest.fixture(autouse=True)
def reset_global_state():
    """
    Clear the module-level mutable state that would otherwise leak between
    tests.

    charts.display.Chart.ident comes from the global random module.
    """
    from stringprint.models import Chrome

    random.seed(0)
    yield
    Chrome.page = None


@pytest.fixture(scope="session")
def org(django_db_setup, django_db_blocker):
    from stringprint.models import Organisation

    with django_db_blocker.unblock():
        organisation, _ = Organisation.objects.get_or_create(slug="default")
        organisation.load_from_yaml()
        yield organisation


SLUGS = ["minimal-doc", "kitchen-sink", "legacy-doc", "multipage-doc"]


@pytest.fixture(scope="session")
def loaded_articles(org, django_db_blocker, doc_folder) -> Dict[str, Any]:
    """
    Every fixture document, loaded but not processed, following the order
    SPPrompt.do_process uses.

    The work happens in the fixture body rather than in a lazily-called
    factory, and that is load-bearing: pytest sets session-scoped fixtures up
    before the function-scoped transaction that pytest.mark.django_db opens, so
    these rows are committed and survive for the whole session. Deferring the
    same work into a callable would put the writes inside the first test's
    transaction, where they would be rolled back - leaving later tests holding
    in-memory objects whose rows no longer exist.

    The corollary is that these rows are shared: a test may read them freely,
    and any change it makes is undone with its own transaction.
    """
    from stringprint.models import Article

    articles = {}
    with django_db_blocker.unblock():
        for slug in SLUGS:
            folder = doc_folder(slug)
            article, _ = Article.objects.get_or_create(org=org, slug=slug)
            article.load_from_yaml(folder)
            article.run_command("preprocess")
            article.load_from_yaml(folder, refresh_header=True)
            article.import_assets(Path(folder, "assets"), True)
            article.load_from_file()
            articles[slug] = article

        # Re-read every article, so the tests work from persisted state
        # rather than whatever the loader happened to leave in memory.
        articles = {
            slug: Article.objects.get(pk=article.pk)
            for slug, article in articles.items()
        }
    return articles


@pytest.fixture(scope="session")
def processed_articles(loaded_articles, django_db_blocker) -> Dict[str, Any]:
    """Every fixture document, processed. See loaded_articles on scoping."""
    with django_db_blocker.unblock():
        for article in loaded_articles.values():
            article.process()
    return loaded_articles


@pytest.fixture(scope="session")
def load_doc(loaded_articles) -> Callable[[str], Any]:
    def get(slug: str):
        return loaded_articles[slug]

    return get


@pytest.fixture(scope="session")
def process_doc(processed_articles) -> Callable[[str], Any]:
    def get(slug: str):
        return processed_articles[slug]

    return get


@pytest.fixture(scope="session")
def kitchen_sink(process_doc):
    return process_doc("kitchen-sink")


@pytest.fixture(scope="session")
def multipage_doc(process_doc):
    return process_doc("multipage-doc")


@pytest.fixture(scope="session")
def minimal_doc(process_doc):
    return process_doc("minimal-doc")


@pytest.fixture(scope="session")
def legacy_doc(process_doc):
    return process_doc("legacy-doc")


class FakeLocator:
    def __init__(self, x: int = 40, y: int = 200, missing: bool = False):
        self._box = None if missing else {"x": x, "y": y, "width": 800, "height": 120}

    def count(self) -> int:
        return 0 if self._box is None else 1

    def bounding_box(self):
        return self._box


class FakeDriver:
    """
    Stands in for a headless Playwright page in export_paragraph_images.

    Chrome.get_page is the only place the real page is built, so replacing
    it lets the surrounding logic - the skip filters, the scroll, the crop
    arithmetic and the output filenames - run for real with no browser and no
    preview server listening on 127.0.0.1:8000.
    """

    def __init__(self, missing_orders=()):
        self.missing_orders = set(missing_orders)
        self.requested_url = None
        self.window_size = None
        self.scrolled_to = []
        self.closed = False

    def set_viewport_size(self, size):
        self.window_size = (size["width"], size["height"])

    def goto(self, url, timeout=None):
        self.requested_url = url

    def locator(self, selector):
        order = int(selector.lstrip("#r"))
        return FakeLocator(missing=order in self.missing_orders)

    def evaluate(self, script):
        self.scrolled_to.append(script)

    def screenshot(self, path, clip):
        from PIL import Image

        width = max(int(clip["width"]), 1)
        height = max(int(clip["height"]), 1)
        Image.new("RGB", (width, height), (255, 255, 255)).save(path, "PNG")

    def close(self):
        self.closed = True


@pytest.fixture
def fake_chrome(monkeypatch):
    """Install FakeDriver as the Chrome singleton for the duration of a test."""
    from stringprint.models import Chrome

    driver = FakeDriver()
    monkeypatch.setattr(Chrome, "page", None)
    monkeypatch.setattr(Chrome, "get_page", classmethod(lambda cls: driver))
    return driver
