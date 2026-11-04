"""
Render persisted publications for the legacy Kindle generator.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from contextlib import nullcontext
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Protocol

from django.conf import settings
from django.contrib.staticfiles import finders
from pydantic import BaseModel, ConfigDict

from stringprint2.services.static_rendering import (
    StaticRenderTarget,
    write_static_view,
)

KindleCommandRunner = Callable[[list[str]], int]


class KindlePublication(Protocol):
    """
    Publication values and relations required for Kindle rendering.
    """

    assets: Any
    book_cover: Any
    slug: str

    def tinify_headers(self) -> None:
        """
        Prepare small header derivatives.
        """

        ...


class KindleRenderResult(BaseModel):
    """
    Describe a completed Kindle-generator invocation.
    """

    model_config = ConfigDict(frozen=True)

    destination: Path
    generated: bool
    return_code: int
    media_count: int


def run_kindle_command(arguments: list[str]) -> int:
    """
    Invoke the configured Kindle generator without a shell.
    """

    return subprocess.call(arguments)


def render_kindle_staging(
    publication: KindlePublication,
    staging: Path,
    destination: Path,
    *,
    image_asset_type: int,
    chart_asset_type: int,
    runner: KindleCommandRunner,
) -> KindleRenderResult:
    """
    Populate one staging directory and invoke the Kindle generator.
    """

    from stringprint2.stringprint.views import (
        KindleNCX,
        KindleOPF,
        KindleView,
    )

    publication.tinify_headers()

    css_directory = staging / "css"
    media_directory = staging / "media"
    css_directory.mkdir(parents=True, exist_ok=True)
    media_directory.mkdir(parents=True, exist_ok=True)
    opf = staging / f"{publication.slug}.opf"

    media_files: list[str] = []
    for asset in publication.assets.filter(active=True):
        if asset.type == image_asset_type:
            media_files.append(asset.get_image_name(1200))
        elif asset.type == chart_asset_type and asset.chart.chart_type != "table_chart":
            media_files.append(asset.image_chart.name)
    for filename in media_files:
        shutil.copyfile(
            Path(settings.MEDIA_ROOT) / filename, media_directory / filename
        )

    targets = (
        (KindleView, staging / "text.html"),
        (KindleOPF, opf),
        (KindleNCX, staging / "toc.ncx"),
    )
    for view, output in targets:
        write_static_view(
            view,
            StaticRenderTarget(
                destination=output,
                request_path=str(output),
                minimise=False,
            ),
            (publication.slug,),
            transform=lambda content: content.replace(
                f"{settings.STATIC_URL}css/kindle.css", "css/kindle.css"
            ),
            view_options={"publication": publication},
        )

    stylesheet = finders.find("css/kindle.css")
    if stylesheet is None:
        raise FileNotFoundError("Could not find css/kindle.css")
    shutil.copyfile(stylesheet, css_directory / "kindle.css")
    if publication.book_cover and Path(publication.book_cover.path).exists():
        shutil.copyfile(publication.book_cover.path, staging / "bookcover.jpg")

    generator = str(getattr(settings, "KINDLEGEN_LOC", "") or "kindlegen")
    return_code = runner([generator, str(opf)])
    generated_file = staging / f"{publication.slug}.mobi"
    destination_file = destination / generated_file.name
    generated = generated_file.exists()
    if not generated or return_code not in {0, 1}:
        raise RuntimeError(
            f"Kindle generation failed (exit {return_code}): {generator} did not produce a usable MOBI file."
        )
    if generated and generated_file != destination_file:
        shutil.copyfile(generated_file, destination_file)
    return KindleRenderResult(
        destination=destination_file,
        generated=generated,
        return_code=return_code,
        media_count=len(media_files),
    )


def render_kindle(
    publication: KindlePublication,
    destination: Path,
    *,
    use_temporary_directory: bool = False,
    image_asset_type: int,
    chart_asset_type: int,
    runner: KindleCommandRunner | None = None,
) -> KindleRenderResult:
    """
    Render a Kindle publication, cleaning temporary staging automatically.
    """

    generator = str(getattr(settings, "KINDLEGEN_LOC", "") or "kindlegen")
    if runner is None and shutil.which(generator) is None:
        raise FileNotFoundError(
            f"Kindle generator '{generator}' is unavailable. Set KINDLEGEN_LOC to an installed generator, or use EPUB instead."
        )
    destination.mkdir(parents=True, exist_ok=True)
    context = (
        TemporaryDirectory()
        if use_temporary_directory
        else nullcontext(str(destination))
    )
    with context as staging_directory:
        return render_kindle_staging(
            publication,
            Path(staging_directory),
            destination,
            image_asset_type=image_asset_type,
            chart_asset_type=chart_asset_type,
            runner=runner or run_kindle_command,
        )
