"""Tests for worker availability in the management interface."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from frontend.models import UserSettings
from publication_management.worker_health import register_publication_worker


@pytest.mark.django_db
def test_publication_list_distinguishes_available_worker(client, org) -> None:
    """An idle worker is visible independently of whether operations exist."""
    user = User.objects.create_user(username="manager", password="secret")
    UserSettings.objects.create(user=user, org=org)
    client.force_login(user)
    url = reverse("publication_management:publication_list")

    unavailable = client.get(url)
    register_publication_worker("host:10", "host", 10)
    available = client.get(url)

    assert b"worker unavailable" in unavailable.content
    assert b"worker available" in available.content
