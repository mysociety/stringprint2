"""Source-authoring screens never silently change only the database."""

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from frontend.models import UserSettings

pytestmark = pytest.mark.django_db


def test_source_settings_are_read_only(client, org, kitchen_sink):
    user = User.objects.create_user(username="source-reader", password="test")
    UserSettings.join(user, org)
    client.force_login(user)
    title = kitchen_sink.title
    name = org.name
    for route, args, data in [
        ("article.settings", (kitchen_sink.pk,), {"title": "Changed"}),
        ("org.settings", (), {"name": "Changed"}),
        ("article.headers", (kitchen_sink.pk,), {"image_alt": "Changed"}),
    ]:
        url = reverse(route, args=args)
        response = client.get(url)
        assert response.status_code == 200
        assert b"settings.yaml" in response.content
        assert client.post(url, data).status_code == 405
    kitchen_sink.refresh_from_db()
    org.refresh_from_db()
    assert kitchen_sink.title == title
    assert org.name == name


@pytest.mark.parametrize(
    "route",
    ["article.settings", "article.headers", "article.publish", "document.reupload"],
)
def test_article_pages_require_authentication_and_organisation_membership(
    client, org, route
):
    from stringprint.models import Article, Organisation

    other = Organisation.objects.create(
        slug="private-publisher", name="Private publisher"
    )
    article = Article.objects.create(org=other, slug="private-document")
    url = reverse(route, args=(article.pk,))
    response = client.get(url)
    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))
    user = User.objects.create_user(username="reader", password="test")
    client.force_login(user)
    assert client.get(url).status_code == 403
    UserSettings.join(user, org)
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == reverse("home")


def test_settings_support_head_without_changing_content(client, org):
    user = User.objects.create_user(username="head-reader", password="test")
    UserSettings.join(user, org)
    client.force_login(user)
    response = client.head(reverse("org.settings"))
    assert response.status_code == 200
    assert response.content == b""
