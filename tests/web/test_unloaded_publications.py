"""Tests for discovering and initially loading source-only publications."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from frontend.models import UserSettings
from publication_management.models import PublicationOperation
from stringprint.models import Article


@pytest.mark.django_db
def test_dashboard_lists_unloaded_source_and_enqueues_initial_load(client, org) -> None:
    """The web interface can bootstrap a publication without creating it inline."""
    Article.objects.filter(org=org, slug="minimal-doc").delete()
    user = User.objects.create_user(username="manager", password="secret")
    UserSettings.objects.create(user=user, org=org)
    client.force_login(user)

    listing = client.get(reverse("publication_management:publication_list"))
    response = client.post(
        reverse(
            "publication_management:create_operation",
            args=("minimal-doc", "load"),
        )
    )

    operation = PublicationOperation.objects.get(publication_slug="minimal-doc")
    assert listing.status_code == 200
    assert b"minimal-doc" in listing.content
    assert b"not loaded" in listing.content
    assert response.status_code == 302
    assert operation.article is None
    assert operation.operation_name == "load"


@pytest.mark.django_db
@pytest.mark.parametrize("slug", ["missing", "../_conf"])
def test_initial_load_rejects_unknown_source_slug(client, org, slug) -> None:
    """A crafted load URL cannot address files outside discovered sources."""
    user = User.objects.create_user(username=f"manager-{slug}", password="secret")
    UserSettings.objects.create(user=user, org=org)
    client.force_login(user)

    response = client.post(
        reverse(
            "publication_management:create_operation",
            args=(slug, "load"),
        )
        if "/" not in slug
        else "/manage/publications/../_conf/load/"
    )

    assert response.status_code == 404
    assert not PublicationOperation.objects.exists()
