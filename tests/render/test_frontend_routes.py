"""Tests for deliberately retired frontend routes."""

from __future__ import annotations

import pytest
from django.template.loader import get_template
from django.urls import NoReverseMatch, reverse


def test_rich_text_editor_route_is_not_registered() -> None:
    """Source-file authoring has replaced the browser rich-text editor."""
    with pytest.raises(NoReverseMatch):
        reverse("article.edit", args=(1,))


def test_search_template_uses_native_search_module() -> None:
    """Published search no longer loads the jQuery Tipue plugin."""
    source = get_template("ink/search.html").template.source

    assert "document_search.js" in source
    assert "tipuesearch.min.js" not in source
    assert "tipuesearch_set.js" not in source


def test_article_template_uses_native_menu_module() -> None:
    """Published menus no longer load Bootstrap's jQuery plugins or Popper."""
    source = get_template("ink/article.html").template.source

    assert "document_menus.js" in source
    assert "popper.min.js" not in source
    assert "bootstrap/js/dist/dropdown.js" not in source
    assert "bootstrap/js/dist/collapse.js" not in source
