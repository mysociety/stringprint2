"""Compatibility tests for the retired legacy publish screen."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from frontend.models import UserSettings
from stringprint.models import Article


@pytest.mark.django_db
def test_legacy_publish_url_redirects_to_operation_management(client, org) -> None:
    """Existing links remain useful without calling removed render/download APIs."""
    user = User.objects.create_user(username="manager", password="secret")
    UserSettings.objects.create(user=user, org=org)
    article = Article.objects.create(org=org, slug="managed", title="Managed")
    client.force_login(user)

    response = client.get(reverse("article.publish", args=(article.pk,)))

    assert response.status_code == 302
    assert response.url == reverse(
        "publication_management:publication_detail",
        args=(article.slug,),
    )


@pytest.mark.django_db
def test_legacy_publish_url_retains_organisation_scope(client, org) -> None:
    """A known numeric ID cannot redirect a user to another organisation."""
    from stringprint.models import Organisation

    user = User.objects.create_user(username="manager", password="secret")
    UserSettings.objects.create(user=user, org=org)
    other = Organisation.objects.create(slug="other", name="Other")
    article = Article.objects.create(org=other, slug="private", title="Private")
    client.force_login(user)

    response = client.get(reverse("article.publish", args=(article.pk,)))

    assert response.status_code == 302
    assert response.url == reverse("home")
