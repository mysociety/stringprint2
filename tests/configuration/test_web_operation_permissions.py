"""Tests for explicit authored web-operation permissions."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from stringprint2.configuration.models import PublicationConfig


def publication_values() -> dict[str, object]:
    """Return the required fields for one publication configuration."""
    return {
        "title": "Example",
        "short_title": "Example",
        "description": "Example",
        "byline": None,
        "authors": None,
        "cite_as": "Example",
        "file_source": "document.md",
        "publish_date": date(2026, 1, 1),
        "repo_slug": "example",
    }


def test_publish_requires_an_explicit_allow_list_entry() -> None:
    """Potentially external web actions default to unavailable."""
    default = PublicationConfig.model_validate(publication_values())
    allowed = PublicationConfig.model_validate(
        {**publication_values(), "web_operations": ["publish"]}
    )

    assert default.web_operations == []
    assert allowed.web_operations == ["publish"]


def test_arbitrary_configured_commands_cannot_be_web_enabled() -> None:
    """The allow-list schema is closed rather than accepting command names."""
    with pytest.raises(ValidationError):
        PublicationConfig.model_validate(
            {**publication_values(), "web_operations": ["preprocess"]}
        )
