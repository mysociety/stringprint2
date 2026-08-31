"""
Tests for project-owned static view rendering.
"""

from __future__ import annotations

from pathlib import Path

from django.http import HttpResponse
from stringprint2.services import (
    StaticRenderTarget,
    render_static_view,
    write_static_view,
)


class ExampleView:
    """
    Return request and positional values for renderer assertions.
    """

    @classmethod
    def as_view(cls, decorators: bool = True):
        def view(request, value: str) -> HttpResponse:
            return HttpResponse(
                f"<html><body>{request.path}:{value}:{decorators}</body></html>"
            )

        return view


def target(destination: Path, minimise: bool = True) -> StaticRenderTarget:
    """
    Build a static render target for a test destination.
    """
    return StaticRenderTarget(
        destination=destination,
        request_path="/preview/example/",
        minimise=minimise,
    )


def test_rendering_uses_the_explicit_request_path(tmp_path: Path) -> None:
    content = render_static_view(ExampleView, target(tmp_path / "page.html"), ["ok"])

    assert "/preview/example/:ok:False" in content


def test_writing_creates_parent_directories(tmp_path: Path) -> None:
    destination = tmp_path / "nested" / "page.html"

    write_static_view(ExampleView, target(destination), ["written"])

    assert "written" in destination.read_text(encoding="utf-8")


def test_transform_runs_before_the_atomic_write(tmp_path: Path) -> None:
    destination = tmp_path / "page.html"

    write_static_view(
        ExampleView,
        target(destination),
        ["before"],
        transform=lambda content: content.replace("before", "after"),
    )

    assert "after" in destination.read_text(encoding="utf-8")
    assert not (tmp_path / ".page.html.tmp").exists()
