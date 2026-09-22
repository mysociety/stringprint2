"""Authentication regressions for the legacy management interface."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.urls import reverse


@pytest.mark.django_db
def test_unassigned_user_cannot_open_legacy_dashboard(client, org) -> None:
    """Legacy views do not grant the first organisation to an arbitrary user."""
    user = User.objects.create_user(username="unassigned", password="secret")
    client.force_login(user)

    response = client.get(reverse("home"))

    assert response.status_code == 403
    assert not user.settings.exists()
