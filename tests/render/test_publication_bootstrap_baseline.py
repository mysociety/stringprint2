"""Migration baselines for the publication-facing Bootstrap integration."""

from __future__ import annotations

from pathlib import Path

import pytest
from django.template.loader import get_template

pytestmark = pytest.mark.django_db

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_SCSS = PROJECT_ROOT / "stringprint2" / "vendor" / "bootstrap" / "scss"
STRINGPRINT_SCSS = PROJECT_ROOT / "stringprint2" / "web" / "scss" / "stringprint"


def test_publication_pipeline_uses_bootstrap_5_3_8() -> None:
    """Publication SCSS is built from the pinned Bootstrap 5 release."""
    bootstrap = (BOOTSTRAP_SCSS.parent / "README.md").read_text()

    assert "Bootstrap 5.3.8" in bootstrap


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
        "variables-dark",
        "maps",
        "mixins",
        "utilities",
        "root",
        "reboot",
        "tables",
        "buttons",
        "transitions",
        "dropdown",
        "forms/input-group",
        "nav",
        "navbar",
        "helpers/position",
        "utilities/api",
    ]
    assert "modal" not in source
    assert "carousel" not in source
    assert '@import "print"' not in source


def test_publication_templates_use_bootstrap_5_component_contract() -> None:
    """Navigation, search, and tables use Bootstrap 5 component markup."""
    navigation = get_template("ink/article_nav.html").template.source
    search = get_template("ink/search.html").template.source
    table = get_template("charts/bootstrap_table.html").template.source

    assert "navbar-expand-md" in navigation
    assert "me-auto" in navigation
    assert "ms-auto" in navigation
    assert "dropdown-menu-end" in navigation
    assert "data-menu-toggle" in navigation
    assert "mr-auto" not in navigation
    assert "ml-auto" not in navigation
    assert "data-toggle=" not in navigation
    assert "input-group-append" not in search
    assert "table-light" in table
    assert "thead-light" not in table


def test_live_publication_exposes_navigation_and_content_contract(
    client,
    kitchen_sink,
) -> None:
    """A live report retains desktop/mobile navigation and canonical content anchors."""
    response = client.get(f"/preview/{kitchen_sink.slug}/")
    page = response.content.decode("utf-8")

    assert response.status_code == 200
    assert 'class="d-none d-md-flex navbar' in page
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

    assert 'class="input-group mb-3"' in search
    assert "input-group-append" not in search
    assert 'id="publication-search-input"' in search
    assert 'class="table table-striped"' in article
    assert 'class="table-light"' in article


def test_publication_navigation_has_valid_accessible_controls(
    client,
    kitchen_sink,
) -> None:
    """Rendered menus use buttons for controls and valid list nesting."""
    from bs4 import BeautifulSoup

    page = client.get(f"/preview/{kitchen_sink.slug}/").content.decode()
    soup = BeautifulSoup(page, "html.parser")
    toggles = soup.select("button[data-menu-toggle]")

    assert toggles
    assert all(toggle.get("aria-expanded") == "false" for toggle in toggles)
    assert soup.select_one(
        "#mobile-menu-toggle[aria-controls='navbarSupportedContent']"
    )
    assert not soup.select("ul > button")
    assert not soup.select("[data-toggle], [data-target]")
