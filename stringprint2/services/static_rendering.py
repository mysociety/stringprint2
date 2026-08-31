"""
Render Django views to static files without the vendored bake framework.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol, cast

from django.conf import settings
from django.http import HttpResponse
from django.test.client import RequestFactory
from htmlmin.minify import html_minify as untyped_html_minify  # type: ignore[import-untyped]

html_minify = cast(Callable[[bytes], bytes], untyped_html_minify)
from pydantic import BaseModel, ConfigDict


class StaticView(Protocol):
    """
    Describe the class-level view adapter used by Stringprint views.
    """

    @classmethod
    def as_view(cls, decorators: bool = True) -> Callable[..., HttpResponse]:
        """
        Return a Django-compatible view callable.
        """
        ...


class StaticRenderTarget(BaseModel):
    """
    Describe one filesystem destination and its synthetic request path.
    """

    model_config = ConfigDict(frozen=True)

    destination: Path
    request_path: str
    minimise: bool = True


def render_static_view(
    view: type[StaticView],
    target: StaticRenderTarget,
    arguments: Sequence[object],
) -> str:
    """
    Render a view response to text without writing to the filesystem.
    """
    request = RequestFactory().get(target.request_path)
    content = view.as_view(decorators=False)(request, *arguments).content
    if b"<html" in content and target.minimise:
        content = html_minify(content)
    if isinstance(content, bytes):
        return content.decode("utf-8", errors="ignore")
    return str(content)


def write_static_view(
    view: type[StaticView],
    target: StaticRenderTarget,
    arguments: Sequence[object],
    transform: Callable[[str], str] | None = None,
) -> None:
    """
    Render and atomically write one static view target.
    """
    content = render_static_view(view, target, arguments)
    if transform is not None:
        content = transform(content)

    target.destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = target.destination.with_name(f".{target.destination.name}.tmp")
    temporary_path.write_text(content, encoding="utf-8")
    os.replace(temporary_path, target.destination)


def relativize_static_urls(content: str, depth: int) -> str:
    """
    Rewrite absolute static and media URLs relative to a baked page.
    """

    prefix = "../" * depth
    content = content.replace(settings.STATIC_URL, prefix + "static/")
    return content.replace(settings.MEDIA_URL, prefix + "media/")


def write_baked_file(
    view: type[StaticView],
    path: Path,
    arguments: Sequence[object],
    destination: Path,
) -> None:
    """
    Render one view through the atomic renderer with relative asset URLs.
    """

    relative_directory = os.path.relpath(path.parent, destination)
    depth = 0 if relative_directory == "." else len(Path(relative_directory).parts)
    target = StaticRenderTarget(destination=path, request_path=str(path))
    write_static_view(
        view,
        target,
        arguments,
        transform=lambda content: relativize_static_urls(content, depth),
    )
