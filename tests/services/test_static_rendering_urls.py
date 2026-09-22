"""
Tests for baked static and media URL rewriting.
"""

from __future__ import annotations

from django.conf import settings

from stringprint2.services.static_rendering import relativize_static_urls


def test_top_level_baked_urls_point_to_local_asset_directories() -> None:
    content = f"{settings.STATIC_URL}app.css {settings.MEDIA_URL}image.png"

    assert relativize_static_urls(content, 0) == "static/app.css media/image.png"


def test_nested_baked_urls_are_relative_to_the_publication_root() -> None:
    content = f"{settings.STATIC_URL}app.css {settings.MEDIA_URL}image.png"

    assert relativize_static_urls(content, 2) == (
        "../../static/app.css ../../media/image.png"
    )
