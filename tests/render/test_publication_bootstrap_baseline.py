"""Migration baselines for the publication-facing Bootstrap integration."""

from __future__ import annotations

from pathlib import Path

import pytest
from django.template.loader import get_template

pytestmark = pytest.mark.django_db

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_SCSS = PROJECT_ROOT / "stringprint2" / "vendor" / "bootstrap" / "scss"
STRINGPRINT_SCSS = PROJECT_ROOT / "stringprint2" / "web" / "scss" / "stringprint"


def test_publication_pipeline_starts_from_bootstrap_4_5() -> None:
    """The migration baseline records the framework currently being replaced."""
    bootstrap = (BOOTSTRAP_SCSS / "bootstrap.scss").read_text()

    assert "Bootstrap v4.5.0" in bootstrap


def test_publication_pipeline_imports_only_required_bootstrap_components() -> None:
    """Publication CSS has a deliberate selective Bootstrap import boundary."""
    source = (STRINGPRINT_SCSS / "bootstrap_import.scss").read_text()
    imports = [
        line.removeprefix('@import "').removesuffix('";')
        for line in source.splitlines()
        if line.startswith("@import")
    ]

    assert imports == [
        "functions",
        "variables",
        "mixins",
        "root",
        "reboot",
        "tables",
        "buttons",
        "transitions",
        "dropdown",
        "input-group",
        "nav",
        "navbar",
        "utilities",
        "print",
    ]
    assert "modal" not in source
    assert "carousel" not in source


def test_publication_templates_record_bootstrap_4_component_contract() -> None:
    """Navigation, search, and tables expose the markup the migration must preserve."""
    navigation = get_template("ink/article_nav.html").template.source
    search = get_template("ink/search.html").template.source
    table = get_template("charts/bootstrap_table.html").template.source

    assert "navbar-expand-md" in navigation
    assert "mr-auto" in navigation
    assert "ml-auto" in navigation
    assert "dropdown-menu-right" in navigation
    assert 'data-toggle="dropdown"' in navigation
    assert "input-group-append" in search
    assert "thead-light" in table


def test_live_publication_exposes_navigation_and_content_contract(
    client,
    kitchen_sink,
) -> None:
    """A live report retains desktop/mobile navigation and canonical content anchors."""
    response = client.get(f"/preview/{kitchen_sink.slug}/")
    page = response.content.decode("utf-8")

    assert response.status_code == 200
    assert 'class="d-sm-none d-md-flex d-lg-flex navbar' in page
    assert 'id="mobile-menu-toggle"' in page
    assert 'id="navbarSupportedContent"' in page
    assert 'id="index"' in page
    assert "data-paragraph-order=" in page
    assert "document_menus.js" in page
    assert "bootstrap/js/" not in page
    assert "jquery" not in page.lower()


def test_search_and_table_components_render_the_bootstrap_4_baseline(
    client,
    kitchen_sink,
) -> None:
    """The two secondary Bootstrap components are covered through real views."""
    search = client.get(f"/preview/{kitchen_sink.slug}/search").content.decode()
    article = client.get(f"/preview/{kitchen_sink.slug}/").content.decode()

    assert 'class="input-group-append"' in search
    assert 'id="publication-search-input"' in search
    assert 'class="table table-striped"' in article
    assert 'class="thead-light"' in article
