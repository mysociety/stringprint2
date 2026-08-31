"""Tests for deliberately retired frontend routes."""

from __future__ import annotations

import pytest
from django.urls import NoReverseMatch, reverse


def test_rich_text_editor_route_is_not_registered() -> None:
    """Source-file authoring has replaced the browser rich-text editor."""
    with pytest.raises(NoReverseMatch):
        reverse("article.edit", args=(1,))
