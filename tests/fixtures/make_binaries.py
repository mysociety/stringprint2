"""
Regenerate the binary fixture files.

Run from the submodule root::

    python tests/fixtures/make_binaries.py

Outputs are committed alongside this script. Re-running must produce
byte-identical files - pass --check to assert that without writing.
"""

from __future__ import annotations

import datetime
import re
import shutil
import sys
import zipfile
from collections.abc import Callable
from pathlib import Path

import pymupdf as fitz
import xlwt
from openpyxl import Workbook
from PIL import Image, ImageDraw

FIXED_TIME = datetime.datetime(2020, 1, 1, 0, 0, 0)
FIXED_PDF_TIME = "D:20200101000000Z"
FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)
FIXED_XLSX_TIME = b"2020-01-01T00:00:00Z"
XLSX_MODIFIED_RE = re.compile(rb"(<dcterms:modified\b[^>]*>).*?(</dcterms:modified>)")

DOC_SOURCE = Path(__file__).parent / "doc_source"
DOCS = DOC_SOURCE / "_docs"
STATIC = DOC_SOURCE / "_static"


def normalise_zip(path: Path) -> None:
    """
    Rewrite a zip with fixed member timestamps.

    openpyxl stamps each member with the current local time, so an xlsx is
    otherwise different on every run.
    """
    source = zipfile.ZipFile(str(path))
    members = []
    for info in source.infolist():
        data = source.read(info.filename)
        if info.filename == "docProps/core.xml":
            data = XLSX_MODIFIED_RE.sub(
                rb"\g<1>" + FIXED_XLSX_TIME + rb"\g<2>",
                data,
            )
        members.append((info, data))
    source.close()

    temporary = path.with_suffix(path.suffix + ".tmp")
    with zipfile.ZipFile(str(temporary), "w", zipfile.ZIP_DEFLATED) as target:
        for info, data in members:
            fixed = zipfile.ZipInfo(info.filename, date_time=FIXED_ZIP_TIME)
            fixed.compress_type = info.compress_type
            fixed.external_attr = info.external_attr
            target.writestr(fixed, data)
    shutil.move(str(temporary), str(path))


# The two /ID elements are each either a hex string or a literal string -
# fitz picks whichever encodes its random bytes more compactly, so the form
# varies from run to run and both have to be matched.
PDF_ID_ELEMENT = rb"(?:<[0-9A-Fa-f]*>|\((?:\\.|[^\\()])*\))"
PDF_ID_RE = re.compile(
    rb"/ID\s*\[\s*" + PDF_ID_ELEMENT + rb"\s*" + PDF_ID_ELEMENT + rb"\s*\]",
    re.DOTALL,
)
FIXED_PDF_ID = b"/ID[<" + b"0" * 32 + b"><" + b"0" * 32 + b">]"


def normalise_pdf(path: Path) -> None:
    """
    Replace the trailer /ID, which fitz derives from random bytes.
    """
    data, count = PDF_ID_RE.subn(FIXED_PDF_ID, path.read_bytes())
    if count != 1:
        raise ValueError(
            "expected exactly one /ID in {0}, found {1} - the pdf would not "
            "reproduce byte-identically".format(path, count)
        )
    path.write_bytes(data)


def make_image(path: Path, size: tuple[int, int], fmt: str) -> None:
    """
    A flat ground plus two blocks of colour.

    Width is 1920 for the header and asset images on purpose: create_responsive
    generates 768/992/1200/1440/1920, so the widest tier hits the
    "new size is larger than original" branch while the rest genuinely resize.
    The extra colours keep get_average_color's quantize(colors=2) from
    collapsing to a degenerate result.
    """
    width, height = size
    image = Image.new("RGB", size, (34, 68, 102))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, width // 3, height], fill=(221, 238, 255))
    draw.rectangle([width // 3, 0, 2 * width // 3, height // 2], fill=(153, 0, 51))
    if fmt == "JPEG":
        image.save(path, fmt, quality=60, optimize=True)
    else:
        image.save(path, fmt, optimize=True)


def make_xls(path: Path) -> None:
    """
    Column headings chosen to exercise charts.display.Column:

    * "Year"                -> col_type forced to string
    * "%"                   -> format "{0:.0f}%", multiple 100
    * "Cost [[currency]]"   -> format "GBP{:20,.0f}", marker stripped from name
    * "Region||split["      -> the split[ setting, values "<number>[<label>]"
    """
    book = xlwt.Workbook()
    sheet = book.add_sheet("Sheet 1")
    headers = ["Year", "%", "Cost [[currency]]", "Region||split["]
    rows = [
        ["2019", 0.125, 1400, "12[north]"],
        ["2020", 0.33, 2600, "24[east]"],
        ["2021", 0.5125, 900, "36[south]"],
        ["2022", 1.0, 17500, "48[west]"],
    ]
    for column, value in enumerate(headers):
        sheet.write(0, column, value)
    for row_number, row in enumerate(rows, start=1):
        for column, value in enumerate(row):
            sheet.write(row_number, column, value)
    book.save(str(path))


def make_xlsx(path: Path) -> None:
    book = Workbook()
    sheet = book.active
    for row in [["Alpha", "1", "2"], ["Beta", "3", "4"], ["Gamma", "5", "6"]]:
        sheet.append(row)
    # openpyxl stamps the current time into docProps by default, which would
    # make the file unreproducible
    book.properties.created = FIXED_TIME
    book.properties.modified = FIXED_TIME
    book.save(str(path))
    normalise_zip(path)


def make_pdf(path: Path, text: str, pages: int = 1) -> None:
    document = fitz.open()
    for number in range(pages):
        page = document.new_page()
        page.insert_text((72, 144), "{0} page {1}".format(text, number))
    # same reason as make_xlsx - fitz writes CreationDate/ModDate otherwise
    document.set_metadata({"creationDate": FIXED_PDF_TIME, "modDate": FIXED_PDF_TIME})
    document.save(str(path))
    document.close()
    normalise_pdf(path)


def targets() -> list[tuple[Path, Callable[[Path], None]]]:
    kitchen = DOCS / "kitchen-sink"
    return [
        (kitchen / "header.png", lambda p: make_image(p, (1920, 1080), "PNG")),
        (
            kitchen / "kitchen-sink-cover.png",
            lambda p: make_image(p, (600, 900), "PNG"),
        ),
        (
            kitchen / "assets" / "image-one.png",
            lambda p: make_image(p, (1920, 1080), "PNG"),
        ),
        (
            kitchen / "assets" / "image-two.jpg",
            lambda p: make_image(p, (1920, 1080), "JPEG"),
        ),
        # smaller than every responsive width, so no tier is downsized
        (
            kitchen / "assets" / "image-three.png",
            lambda p: make_image(p, (400, 300), "PNG"),
        ),
        (kitchen / "assets" / "table-one.xls", make_xls),
        (kitchen / "assets" / "table-no-header-one.xlsx", make_xlsx),
        (kitchen / "kitchen-sink.pdf", lambda p: make_pdf(p, "Kitchen sink contents")),
        (kitchen / "cover.pdf", lambda p: make_pdf(p, "Kitchen sink cover")),
        # three pages, so merge_pdfs' start_page actually drops something
        (kitchen / "contents.pdf", lambda p: make_pdf(p, "Kitchen sink body", pages=3)),
        (
            DOCS / "legacy-doc" / "header.png",
            lambda p: make_image(p, (1920, 1080), "PNG"),
        ),
        (
            DOCS / "legacy-doc" / "extra_download.pdf",
            lambda p: make_pdf(p, "Extra download"),
        ),
        (
            DOCS / "multipage-doc" / "background.jpg",
            lambda p: make_image(p, (1920, 600), "JPEG"),
        ),
        (STATIC / "images" / "test_icon.png", lambda p: make_image(p, (64, 64), "PNG")),
    ]


def main(check: bool = False) -> int:
    mismatched: list[str] = []
    for path, builder in targets():
        path.parent.mkdir(parents=True, exist_ok=True)
        if check:
            if not path.exists():
                mismatched.append("{0} (missing)".format(path))
                continue
            before = path.read_bytes()
            builder(path)
            if path.read_bytes() != before:
                mismatched.append("{0} (changed)".format(path))
            path.write_bytes(before)
        else:
            builder(path)
            print("wrote {0} ({1} bytes)".format(path, path.stat().st_size))

    if mismatched:
        print("mismatched:\n  " + "\n  ".join(mismatched))
        return 1
    if check:
        print("all binary fixtures reproduce byte-identically")
    return 0


if __name__ == "__main__":
    sys.exit(main(check="--check" in sys.argv))
