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

    deepink.Footnote keeps note_count and all at class level; process_ink
    resets the first but never the second, so Footnote.all grows for the life
    of the process. That matters because connect_to_footnote scans it for an
    entry with empty content and a matching local_ref, so one document's
    unresolved footnote can capture a later document's definition.

    charts.display.Chart.ident comes from the global random module.
    """
    from stringprint.models import Chrome
    from stringprint.tools.deepink import Footnote

    Footnote.note_count = 0
    Footnote.all = []
    random.seed(0)
    yield
    Footnote.note_count = 0
    Footnote.all = []
    Chrome.driver = None


@pytest.fixture(autouse=True)
def restore_mutated_settings():
    """
    Article.render() sets these on the settings module and never puts them
    back, so without this the tests that follow a render see the baked values.
    """
    names = [
        "MEDIA_URL",
        "MEDIA_ROOT",
        "STATIC_URL",
        "COMPRESS_URL",
        "SITE_ROOT",
        "DEBUG",
        "COMPRESS_ENABLED",
    ]
    saved = {name: getattr(settings, name) for name in names}
    yield
    for name, value in saved.items():
        setattr(settings, name, value)


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

        # Re-read every article, because JsonBlockField(default={}) hands every
        # unsaved instance the *same* dict object - so after the loop all four
        # in-memory articles share one extra_values holding the last document's
        # values. Each database row is written correctly at its own save(), so
        # a round trip through the database is what separates them again.
        # See tests/config/test_shared_field_defaults.py.
        articles = {
            slug: Article.objects.get(pk=article.pk)
            for slug, article in articles.items()
        }
    return articles


@pytest.fixture(scope="session")
def processed_articles(loaded_articles, django_db_blocker) -> Dict[str, Any]:
    """Every fixture document, processed. See loaded_articles on scoping."""
    from stringprint.tools.deepink import Footnote

    with django_db_blocker.unblock():
        for article in loaded_articles.values():
            # documents are processed in turn in one go, so the per-test reset
            # in reset_global_state is not enough on its own here
            Footnote.note_count = 0
            Footnote.all = []
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

