"""Reading content must never create versions or destroy conflicting content."""

import pytest

from stringprint2.stringprint.models import Article, Version

pytestmark = pytest.mark.django_db


def test_missing_content_read_does_not_create_version(org):
    article = Article.objects.create(org=org, slug="missing-content")
    with pytest.raises(Version.DoesNotExist):
        article.content()
    assert not article.versions.exists()
    version = article.ensure_content()
    assert article.content().pk == version.pk
    assert article.ensure_content().pk == version.pk


def test_duplicate_versions_are_preserved_for_explicit_repair(org):
    article = Article.objects.create(org=org, slug="duplicate-content")
    versions = Version.objects.bulk_create(
        [
            Version(article=article, number=article.current_version, raw="First draft"),
            Version(
                article=article, number=article.current_version, raw="Second draft"
            ),
        ]
    )
    before = list(article.versions.order_by("pk").values())
    for lookup in (article.content, article.ensure_content):
        with pytest.raises(Version.MultipleObjectsReturned):
            lookup()
        assert list(article.versions.order_by("pk").values()) == before
    assert len(versions) == 2
