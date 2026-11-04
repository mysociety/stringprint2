"""
Tests for native authenticated-interface form widgets.
"""

from __future__ import annotations

from stringprint2.frontend.forms import ArticlePublishForm, PageHeaderImageForm
from stringprint2.stringprint.models import Article, HeaderImage
import pytest


def test_publish_date_uses_native_date_input() -> None:
    """
    Publishing no longer requires the jQuery UI datepicker.
    """

    form = ArticlePublishForm()

    assert form.fields["publish_date"].widget.input_type == "date"


def test_header_image_widget_renders_with_djangos_form_renderer() -> None:
    """
    Retained image forms accept Django's renderer argument.
    """
    assert 'type="file"' in str(PageHeaderImageForm()["image"])


@pytest.mark.django_db
def test_header_changes_use_existing_derivative_methods(org, monkeypatch) -> None:
    """
    Saving retained image settings invokes real model APIs instead of a removed queue.
    """
    article = Article.objects.create(org=org, slug="header-settings")
    header = HeaderImage.objects.create(article=article, size=6)
    calls = []
    monkeypatch.setattr(
        HeaderImage, "create_responsive", lambda self: calls.append("responsive")
    )
    monkeypatch.setattr(HeaderImage, "create_tiny", lambda self: calls.append("tiny"))
    form = PageHeaderImageForm(
        {"size": 8, "image_alt": "Updated description"}, instance=header
    )
    assert form.is_valid(), form.errors
    form.save(article, files={})
    header.refresh_from_db()
    assert header.size == 8
    assert calls == ["responsive", "tiny"]
