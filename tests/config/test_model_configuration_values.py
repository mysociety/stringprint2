"""Custom settings stay separate from model methods and persistence state."""

import pytest
from stringprint2.stringprint.models import Article, Organisation


@pytest.mark.parametrize("model", [Article, Organisation])
def test_custom_values_are_live_without_becoming_instance_attributes(model):
    instance = model(
        extra_values={
            "custom_theme": "first",
            "save": "not a method",
            "_state": "not model state",
        }
    )
    assert instance.custom_theme == "first"
    assert "custom_theme" not in instance.__dict__
    assert callable(instance.save)
    assert instance._state.adding
    instance.extra_values["custom_theme"] = "second"
    assert instance.custom_theme == "second"
    del instance.extra_values["custom_theme"]
    assert not hasattr(instance, "custom_theme")


def test_legacy_field_override_remains_supported():
    article = Article(title="Database title", extra_values={"title": "Authored title"})
    assert article.title == "Authored title"


@pytest.mark.django_db
def test_reloading_organisation_removes_stale_custom_options(org):
    org.extra_values["fonts"] = "Stale font"
    org.save()
    reloaded = Organisation.objects.get(pk=org.pk)
    reloaded.load_from_yaml()
    assert not hasattr(reloaded, "fonts")
    assert "fonts" not in reloaded.extra_values
    assert not hasattr(Organisation.objects.get(pk=org.pk), "fonts")


@pytest.mark.django_db
def test_deferred_custom_values_are_still_available(org):
    org.extra_values["custom_theme"] = "deferred theme"
    org.save()
    reloaded = Organisation.objects.only("pk").get(pk=org.pk)
    assert reloaded.custom_theme == "deferred theme"


@pytest.mark.django_db
def test_reloading_publication_updates_custom_options_on_the_same_instance(
    org, doc_folder
):
    article = Article.objects.create(
        org=org, slug="minimal-doc", extra_values={"repo_entry": "Stale link"}
    )
    assert article.repo_entry == "Stale link"
    article.load_from_yaml(doc_folder("minimal-doc"))
    assert article.repo_entry == article.extra_values["repo_entry"]
    assert article.repo_entry != "Stale link"
    assert Article.objects.get(pk=article.pk).repo_entry == article.repo_entry
