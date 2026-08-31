"""Tests for load and archive management actions."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from frontend.models import UserSettings
from publication_management.models import PublicationOperation
from stringprint.models import Article


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("operation_name", "posted", "expected"),
    [
        ("load", {"refresh_header": "on"}, {"refresh_header": True}),
        ("archive", {"refresh": "on"}, {"refresh": True}),
    ],
)
def test_extended_action_enqueues_typed_parameters(
    client,
    org,
    operation_name,
    posted,
    expected,
) -> None:
    """Load and archive forms submit only their validated fixed options."""
    user = User.objects.create_user(username="manager", password="secret")
    UserSettings.objects.create(user=user, org=org)
    article = Article.objects.create(org=org, slug="managed", title="Managed")
    client.force_login(user)

    response = client.post(
        reverse(
            "publication_management:create_operation",
            args=(article.slug, operation_name),
        ),
        posted,
    )

    operation = PublicationOperation.objects.get()
    assert response.status_code == 302
    assert operation.operation_name == operation_name
    for key, value in expected.items():
        assert operation.parameters[key] is value
