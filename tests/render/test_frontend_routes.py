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

    menus = (
        Path(__file__).resolve().parents[2] / "frontend" / "ts" / "document_menus.ts"
    ).read_text()
    assert '"[data-menu-toggle]"' in menus
    assert 'event.key === "Escape"' in menus
    assert "data-toggle" not in menus

    navigation = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "ts"
        / "document_navigation.ts"
    ).read_text()
    assert "item.dataset.item" in navigation
    assert 'querySelectorAll<HTMLElement>("[data-item]")' in navigation
    assert 'getAttribute("item")' not in navigation


def test_native_document_scripts_control_css_visibility() -> None:
    """Native controls override the stylesheet's initial display state."""
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "ts"
    links = (frontend_root / "document_links.ts").read_text()
    notes = (frontend_root / "document_notes.ts").read_text()

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


def test_authenticated_layout_uses_responsive_bootstrap_shell() -> None:
    """The shared management shell uses a standard navbar without a fixed sidebar."""
    base = get_template("frontend/base.html").template.source
    navigation = get_template("frontend/side_nav.html").template.source
    css_path = (
        Path(__file__).resolve().parents[2]
        / "stringprint2"
        / "static"
        / "css"
        / "stringprint-front.css"
    )
    css = css_path.read_text()

    assert "navbar navbar-expand-lg navbar-dark bg-dark" in base
    assert "container admin-main" in base
    assert "css/bootstrap5.min.css" in base
    assert (
        'data-bs-toggle="collapse"'
        in get_template("frontend/top_nav.html").template.source
    )
    assert "data-toggle=" not in get_template("frontend/top_nav.html").template.source
    assert 'id="wrapper"' not in base
    assert "publication_management:publication_list" in navigation
    assert "publication_management:operation_list" in navigation
    assert 'method="post"' in navigation
    assert ".admin-main" in css
    assert "padding-left: 225px" not in css
