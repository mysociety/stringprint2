"""Tests for deliberately retired frontend routes."""

from __future__ import annotations

from pathlib import Path

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
    assert "publication_search_content" in source
    assert "tipuesearch.min.js" not in source
    assert "tipuesearch_set.js" not in source
    assert 'class="content" id="publication-search-results"' in source
    assert "block title_and_image" in source
    assert "block table_of_contents" in source


def test_article_template_uses_native_menu_module() -> None:
    """Published menus no longer load Bootstrap's jQuery plugins or Popper."""
    source = get_template("ink/article.html").template.source

    assert "document_menus.js" in source
    assert "popper.min.js" not in source
    assert "bootstrap/js/dist/dropdown.js" not in source
    assert "bootstrap/js/dist/collapse.js" not in source
    assert "document_navigation.js" in source
    assert "jquery.waypoints" not in source
    assert "document_links.js" in source
    assert "jquery-3.5.1.min.js" not in source
    assert "stringprint.js" not in source


def test_native_document_scripts_control_css_visibility() -> None:
    """Native controls override the stylesheet's initial display state."""
    links = Path("frontend/ts/document_links.ts").read_text()
    notes = Path("frontend/ts/document_notes.ts").read_text()

    assert "element.style.display" in links
    assert "element.style.display" in notes


def test_authenticated_templates_do_not_load_jquery() -> None:
    """Authenticated and registration bases use native browser behavior."""
    frontend = get_template("frontend/base.html").template.source
    registration = get_template("registration/base.html").template.source
    publication_home = get_template("ink/base.html").template.source

    assert "admin_navigation.js" in frontend
    assert "jquery" not in frontend.lower()
    assert "jquery" not in registration.lower()
    assert "jquery" not in publication_home.lower()
