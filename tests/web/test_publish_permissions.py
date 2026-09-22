"""Tests for explicit web publishing permission."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from frontend.models import UserSettings
from publication_management.models import PublicationOperation
from stringprint.models import Article


@pytest.fixture
def publish_user(client, org):
    """Authenticate one user associated with the fixture organisation."""
    user = User.objects.create_user(username="publisher", password="secret")
    UserSettings.objects.create(user=user, org=org)
    client.force_login(user)
    return user


@pytest.mark.django_db
def test_publish_is_hidden_and_forbidden_by_default(client, publish_user, org) -> None:
    """Having a configured command alone does not expose it through the web."""
    article = Article.objects.create(
        org=org,
        slug="managed",
        title="Managed",
        commands={"publish": "publish-tool"},
    )
    detail_url = reverse(
        "publication_management:publication_detail",
        args=(article.slug,),
    )
    publish_url = reverse(
        "publication_management:create_operation",
        args=(article.slug, "publish"),
    )

    detail = client.get(detail_url)
    response = client.post(publish_url)

    assert b">Publish<" not in detail.content
    assert response.status_code == 403
    assert not PublicationOperation.objects.exists()


@pytest.mark.django_db
def test_explicit_allow_list_enables_fixed_publish_operation(
    client,
    publish_user,
    org,
) -> None:
    """An authored allow-list entry enables only the typed publish workflow."""
    article = Article.objects.create(
        org=org,
        slug="managed",
        title="Managed",
        commands={"publish": "publish-tool"},
        extra_values={"web_operations": ["publish"]},
    )
    detail_url = reverse(
        "publication_management:publication_detail",
        args=(article.slug,),
    )
    publish_url = reverse(
        "publication_management:create_operation",
        args=(article.slug, "publish"),
    )

    detail = client.get(detail_url)
    response = client.post(publish_url, {"refresh": "on"})

    operation = PublicationOperation.objects.get()
    assert b">Publish<" in detail.content
    assert response.status_code == 302
    assert operation.operation_name == "publish"
    assert operation.parameters["render_archive"] is True
    assert operation.parameters["refresh"] is True
