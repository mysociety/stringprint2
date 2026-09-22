"""
Tests for the framework-light publication loading service.
"""

from __future__ import annotations

import stringprint_test_env
from stringprint2.configuration import (
    load_organisation_config,
    load_publication_config,
)
from stringprint2.services import build_publication_load_plan

FIXTURE_SOURCE = stringprint_test_env.FIXTURES / "doc_source"


def render_default(template: str, publication: dict[str, object]) -> str:
    """
    Render the fixture's single-variable organisation defaults.
    """
    return template.replace("{{article.repo_slug}}", str(publication["repo_slug"]))


def load_plan(slug: str, existing_extra_keys: set[str] | None = None):
    """
    Build a plan from one fixture publication.
    """
    organisation = load_organisation_config(FIXTURE_SOURCE / "_conf" / "settings.yaml")
    publication = load_publication_config(
        FIXTURE_SOURCE / "_docs" / slug / "settings.yaml",
        organisation,
    )
    return build_publication_load_plan(
        publication,
        organisation,
        existing_extra_keys or set(),
        render_default,
    )


def assignments(plan) -> dict[str, object]:
    """
    Make assertions against named assignments without changing service types.
    """
    return dict(plan.field_assignments)


def test_legacy_aliases_are_resolved() -> None:
    values = assignments(load_plan("kitchen-sink"))

    assert values["multipage"] is False
    assert values["pdf_file"] == "kitchen-sink.pdf"
    assert "sections_over_pages" not in values
    assert "pdf" not in values


def test_organisation_defaults_become_extra_values() -> None:
    extra_values = load_plan("minimal-doc").extra_values

    assert extra_values["repo_entry"].endswith("minimal-doc")
    assert extra_values["bottom_iframe"].endswith("minimal-doc")


def test_an_authored_empty_value_suppresses_its_default() -> None:
    assert load_plan("legacy-doc").extra_values["bottom_iframe"] is None


def test_existing_extra_keys_remain_extra_values() -> None:
    plan = load_plan("minimal-doc", {"title"})

    assert "title" not in assignments(plan)
    assert plan.extra_values["title"] == "Minimal Document"


def test_missing_pdf_requests_stale_field_cleanup() -> None:
    assert load_plan("minimal-doc").clear_pdf_file
    assert not load_plan("kitchen-sink").clear_pdf_file


def test_header_and_cover_actions_are_explicit() -> None:
    plan = load_plan("kitchen-sink")

    assert plan.header is not None
    assert plan.header.location == "header.png"
    assert plan.book_cover == "kitchen-sink-cover.png"
