"""
JsonBlockField columns must give every instance its own container.

Django only calls a default when it is callable; a dict literal is evaluated
once at class-definition time and handed to every instance that does not set
the attribute. Seven fields were declared that way, across four models, so any
process holding more than one unsaved instance - which is exactly what the
loadall and loadunloaded commands produce - shared one dict between them.

Rows were still written correctly, because whatever the shared dict held at
the moment of save() was what got serialised for that row, which is why this
survived so long unnoticed.
"""

from __future__ import annotations

import pytest

from stringprint.models import Article, Asset, HeaderImage, Organisation

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "model,field",
    [
        (Article, "extra_values"),
        (Article, "commands"),
        (Organisation, "extra_values"),
        (Organisation, "commands"),
        (Organisation, "default_values"),
        (HeaderImage, "extra_values"),
        (Asset, "extra_values"),
    ],
)
def test_two_new_instances_get_separate_containers(model, field: str) -> None:
    first, second = model(), model()
    assert getattr(first, field) is not getattr(second, field)


@pytest.mark.parametrize(
    "model,field",
    [
        (Article, "extra_values"),
        (Organisation, "default_values"),
        (Asset, "extra_values"),
    ],
)
def test_a_write_to_one_instance_is_not_visible_on_another(model, field: str) -> None:
    first, second = model(), model()
    getattr(first, field)["leaked"] = True
    assert getattr(second, field) == {}


def test_defaults_start_empty() -> None:
    assert Article().extra_values == {}
    assert Article().commands == {}


def test_rows_are_still_written_per_document(loaded_articles) -> None:
    for slug, article in loaded_articles.items():
        assert article.extra_values["repo_slug"] == slug
