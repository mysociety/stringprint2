"""
Tests for publication rendering orchestration.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from stringprint2.services.publication_rendering import (
    PublicationRenderFormat,
    render_publication,
)


class FakePublication:
    """
    Record rendering operations without framework or filesystem dependencies.
    """

    def __init__(self) -> None:
        self.operations: list[str] = []

    def render(self, destination: Path, refresh_all: bool = False) -> None:
        self.operations.append(f"web:{destination}:{refresh_all}")

    def create_ebook(self, destination: Path) -> None:
        self.operations.append(f"epub:{destination}")

    def create_kindle(self, destination: Path) -> None:
        self.operations.append(f"kindle:{destination}")


@pytest.mark.parametrize(
    ("output_format", "expected"),
    [
        (PublicationRenderFormat.WEB, "web:/output/publication:True"),
        (PublicationRenderFormat.EPUB, "epub:/output/publication"),
        (PublicationRenderFormat.KINDLE, "kindle:/output/publication"),
    ],
)
def test_render_publication_dispatches_by_format(
    output_format: PublicationRenderFormat,
    expected: str,
) -> None:
    publication = FakePublication()
    destination = Path("/output/publication")

    result = render_publication(
        publication,
        destination,
        output_format,
        refresh=True,
    )

    assert publication.operations == [expected]
    assert result.destination == destination
    assert result.format is output_format
