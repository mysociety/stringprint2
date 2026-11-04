"""Filesystem image transformations, independent of Django models and settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO, Protocol

from PIL import Image
import tinify
from webptools import webplib as webp  # type: ignore[import-untyped]


class ImageFile(Protocol):
    path: str
    file: BinaryIO


class DerivativeImage(Protocol):
    image: ImageFile
    size: int

    def get_responsive_image_name(self, resolution: int, webp: bool = False) -> str: ...
    def get_tiny_responsive_image_name(self, resolution: int) -> str: ...


def create_tiny(source: DerivativeImage, media_root: Path, api_key: str) -> None:
    """

    Passes up to tinyimg to reduce.
    """

    tinify.key = api_key

    images: tuple[tuple[ImageFile, list[int]], ...]
    if hasattr(source, "image_vertical") and source.image_vertical:
        images = (
            (source.image_vertical, [768]),
            (source.image, [992, 1200, 1440, 1920]),
        )
    else:
        images = ((source.image, [768, 992, 1200, 1440, 1920]),)
    for i_file, res in images:
        for width in res:
            file_name = str(media_root / source.get_responsive_image_name(width))
            tiny_name = str(media_root / source.get_tiny_responsive_image_name(width))
            if api_key:
                print("reducing using tinify")
                compressed = tinify.from_file(str(file_name))
                compressed.to_file(tiny_name)
            else:
                # boring and simply reduction of file if not
                # using tinify
                print("using native to reduce")
                img = Image.open(file_name)
                img.save(tiny_name, optimize=True, quality=95)


def create_responsive(
    source: DerivativeImage,
    media_root: Path,
    *,
    is_asset: bool,
    ignore_first: bool = True,
) -> None:
    """
    creates the different sized versions of the header image.

    If vertical image will make the smaller one mirror that.

    Passes up to tinyimg to reduce.
    """

    images: tuple[tuple[ImageFile, list[int]], ...]
    if hasattr(source, "image_vertical") and source.image_vertical:
        images = (
            (source.image_vertical, [768]),
            (source.image, [992, 1200, 1440, 1920]),
        )
    else:
        images = ((source.image, [768, 992, 1200, 1440, 1920]),)

    pos = 0
    for i_file, res in images:
        web_p_files: list[tuple[str, str, float, int]] = []
        print("creating responsive versions")
        image = Image.open(i_file.file)
        o_width, o_height = image.size
        print(source.image.path)
        print(f"original width {o_width}, height {o_height}")

        size_adjustment = {}
        column_size = {}
        if is_asset:
            size_adjustment = {1920: -2, 1440: 2, 1200: 2, 992: 2, 768: 12}
            column_size = {1920: 970 * (5 / 6), 1440: 970 * (5 / 6)}
        for width in res:
            pos += 1
            # if display is being scaled down, reduce size of image
            new_width: float = width
            if (pos > 1 or ignore_first is False) and source.size != -1:
                if width in column_size:
                    new_width = column_size[width]
                    print(f"forcing use of {new_width}")
                else:
                    relative_size = source.size + size_adjustment.get(
                        width, 0
                    )  # in twelves
                    if relative_size > 12:
                        relative_size = 12
                    new_width = (float(new_width) / 12) * relative_size

                if new_width == 960:  # minor adaption so can appear full screen
                    new_width = 970
                print("resizing to {0}".format(new_width))
            new_height = round(new_width * (float(o_height) / o_width))
            thumbnail = image.copy()
            print(f"{new_width=}, {o_width=}, {new_height=}")
            if new_width < o_width and new_width > 1 and new_height > 1:
                thumbnail.thumbnail((new_width, new_height), Image.Resampling.BICUBIC)
            else:
                print("new size is larger than original, not downsizing")
            new_name = str(media_root / source.get_responsive_image_name(width))
            print("saving as {0}".format(new_name))
            if os.path.exists(new_name):
                print("deleting")
                os.remove(new_name)
            thumbnail.save(new_name)
            webp_name = os.path.splitext(new_name)[0] + ".webp"
            web_p_files.append((i_file.path, webp_name, new_width, new_height))
        if os.path.exists(i_file.path) is False:
            image.save(i_file.path)
        for source_name, dest, new_width, new_height in web_p_files:
            if os.path.exists(dest):
                print("deleting")
                os.remove(dest)
            print("creating webp")
            result = webp.cwebp(
                source_name,
                dest,
                f"-lossless -q 100 -resize {new_width} {new_height}",
            )
            if os.path.exists(dest) is False:
                print(result)
                raise ValueError(
                    f"Webp {dest} not created, with settings:"
                    + f"-lossless -q 100 -resize {new_width} {new_height}"
                )
