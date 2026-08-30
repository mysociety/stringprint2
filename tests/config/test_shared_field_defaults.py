"""
JsonBlockField(default={}) shares one dict between every model instance.

Django only calls a default when it is callable; a dict literal is evaluated
once at class-definition time and handed to every instance that does not set
the attribute. Five fields are declared this way: Organisation.default_values,
Organisation.commands, Organisation.extra_values, Article.extra_values,
Article.commands, HeaderImage.extra_values and Asset.extra_values.

Each database row is still written correctly, because whatever the shared dict
holds at the moment of save() is what gets serialised for that row. The damage
is confined to unsaved or long-lived in-memory instances - which is exactly
what the `loadall` and `loadunloaded` commands produce, since they walk many
documents in a single process.

Pinned rather than fixed; see docs/feature-inventory.md.
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
def test_two_new_instances_share_one_dict(model, field: str) -> None:
    first, second = model(), model()
    assert getattr(first, field) is getattr(second, field)


def test_a_write_to_one_instance_is_visible_on_another() -> None:
    first, second = Article(), Article()
    first.extra_values["leaked"] = True
    assert second.extra_values.get("leaked") is True
    del first.extra_values["leaked"]


def test_rows_are_written_correctly_despite_the_shared_dict(
    loaded_articles,
) -> None:
    """
    The saved values are per-document even though the in-memory dict is not,
    which is why the fixtures re-read from the database.
    """
    for slug, article in loaded_articles.items():
        assert article.extra_values["repo_slug"] == slug

    dicts = [id(a.extra_values) for a in loaded_articles.values()]
    assert len(set(dicts)) == len(dicts), "re-read articles should be independent"
