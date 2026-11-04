"""
Regression tests for legacy routes that now lead to publication management.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from frontend.models import UserSettings
from stringprint.models import Article, Organisation

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("name", ["home", "document.list", "document.new"])
def test_old_catalog_routes_redirect_without_creating_articles(
    client, org, name: str
) -> None:
    """
    A POST to a retired upload screen cannot create a database-only publication.
    """
    user = User.objects.create_user(username="legacy", password="secret")
    UserSettings.objects.create(user=user, org=org)
    client.force_login(user)
    response = client.post(reverse(name), {"title": "Unbacked document"})
    assert response.status_code == 302
    assert response.url == reverse("publication_management:publication_list")
    assert not Article.objects.exists()


def test_retired_reupload_preserves_source_and_organisation_scope(client, org) -> None:
    """
    Old upload requests redirect to authorized management without writing files.
    """
    user = User.objects.create_user(username="legacy", password="secret")
    UserSettings.objects.create(user=user, org=org)
    article = Article.objects.create(org=org, slug="existing")
    client.force_login(user)
    response = client.post(
        reverse("document.reupload", args=(article.pk,)),
        {"file": SimpleUploadedFile("source.docx", b"not imported")},
    )
    assert response.status_code == 302
    assert response.url == reverse(
        "publication_management:publication_detail", args=(article.slug,)
    )
    article.refresh_from_db()
    assert not article.file_source

    other = Organisation.objects.create(slug="other", name="Other")
    article.org = other
    article.save()
    response = client.get(reverse("document.reupload", args=(article.pk,)))
    assert response.status_code == 302
    assert response.url == reverse("home")


def test_legacy_org_switch_cannot_grant_membership(client, org) -> None:
    """
    A guessed organisation ID cannot give a user access to its publications.
    """
    user = User.objects.create_user(username="legacy", password="secret")
    membership = UserSettings.objects.create(user=user, org=org)
    other = Organisation.objects.create(slug="other", name="Other")
    client.force_login(user)
    response = client.get(reverse("org.change", args=(other.pk,)))
    assert response.status_code == 403
    membership.refresh_from_db()
    assert membership.org == org


def test_unknown_routes_return_not_found(client) -> None:
    """
    Unknown URLs do not fall through to the former dashboard catch-all.
    """
    assert client.get("/unknown-legacy-route/").status_code == 404
