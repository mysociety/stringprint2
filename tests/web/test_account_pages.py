"""
Behavior checks for the retained account pages and shared template forms.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "name",
    [
        "login",
        "password_reset",
        "password_reset_done",
        "password_reset_complete",
        "register",
    ],
)
def test_account_pages_render(client, name: str) -> None:
    """
    Account templates compile and render with the Bootstrap 5 shared layout.
    """
    response = client.get(reverse(name))
    assert response.status_code == 200
    assert b"bootstrap5.min.css" in response.content


def test_login_reports_invalid_credentials(client) -> None:
    """
    Authentication errors render through the shared native form template.
    """
    response = client.post(
        reverse("login"), {"username": "missing", "password": "incorrect"}
    )
    assert response.status_code == 200
    assert b"didn't match" in response.content


def test_password_change_pages_require_and_support_authentication(client) -> None:
    """
    An authenticated account can render both password-change screens.
    """
    assert client.get(reverse("password_change")).status_code == 302
    user = User.objects.create_user(username="account", password="secret")
    client.force_login(user)
    assert client.get(reverse("password_change")).status_code == 200
    assert client.get(reverse("password_change_done")).status_code == 200
