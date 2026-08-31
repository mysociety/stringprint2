"""Tabular file loading used by charts and Word-table extraction."""

from __future__ import annotations

import csv
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import xlrd  # type: ignore[import-untyped]
import xlwt  # type: ignore[import-untyped]
from openpyxl import load_workbook  # type: ignore[import-untyped]

type CellValue = None | bool | int | float | str


def file_path(value: str | Path | Sequence[str | Path]) -> Path:
    """Normalize a path or legacy sequence of path components."""
    if isinstance(value, str | Path):
        return Path(value)
    return Path(*value)


class DataTable:
    """An in-memory table with file-format adapters used by Stringprint."""

    def __init__(
        self,
        header: Sequence[CellValue] | None = None,
        rows: Sequence[Sequence[CellValue]] | None = None,
    ) -> None:
        self.header = list(header or [])
        self.data = [list(row) for row in rows or []]
        self.filename: Path | None = None

    def open(
        self,
        filename: str | Path | Sequence[str | Path],
        tab: str | int = "",
        header_row: int = 0,
    ) -> DataTable:
        """Load a CSV, XLS, or XLSX file and return this table."""
        self.filename = file_path(filename)
        suffix = self.filename.suffix.lower()
        if suffix == ".csv":
            rows = self.read_csv(self.filename)
        elif suffix == ".xls":
            rows = self.read_xls(self.filename, tab)
        elif suffix == ".xlsx":
            rows = self.read_xlsx(self.filename, tab)
        else:
            raise ValueError(f"Unsupported table format: {suffix or '<none>'}")

        try:
            self.header = next(rows)
        except StopIteration:
            self.header = []
            self.data = []
            return self
        for _ in range(header_row):
            try:
                self.header = next(rows)
            except StopIteration:
                self.header = []
                self.data = []
                return self
        self.data = list(rows)
        return self

    @staticmethod
    def read_csv(path: Path) -> Iterator[list[CellValue]]:
        """Yield rows from a UTF-8 CSV file."""
        with path.open(encoding="utf-8-sig", newline="") as source:
            for row in csv.reader(line.replace("\0", "") for line in source):
                yield list(row)

    @staticmethod
    def read_xls(path: Path, tab: str | int) -> Iterator[list[CellValue]]:
        """Yield rows from a legacy XLS workbook."""
        workbook = xlrd.open_workbook(filename=str(path))
        sheet = (
            workbook.sheet_by_index(tab if isinstance(tab, int) else 0)
            if tab == "" or isinstance(tab, int)
            else workbook.sheet_by_name(tab)
        )
        for row_index in range(sheet.nrows):
            yield [
                sheet.cell(row_index, column_index).value
                for column_index in range(sheet.ncols)
            ]

    @staticmethod
    def read_xlsx(path: Path, tab: str | int) -> Iterator[list[CellValue]]:
        """Yield rows from an XLSX workbook without loading formulas."""
        workbook = load_workbook(filename=path, read_only=True, data_only=True)
        sheet_name = (
            workbook.sheetnames[tab]
            if isinstance(tab, int)
            else tab or workbook.sheetnames[0]
        )
        for row in workbook[sheet_name].iter_rows(values_only=True):
            yield list(row)

    def save(
        self,
        filename: str | Path | Sequence[str | Path] | None = None,
    ) -> None:
        """Save the table as CSV, PSV, or legacy XLS."""
        target = file_path(filename) if filename is not None else self.filename
        if target is None:
            raise ValueError("No filename given")
        suffix = target.suffix.lower()
        if suffix in {".csv", ".psv"}:
            delimiter = "|" if suffix == ".psv" else ","
            with target.open("w", encoding="utf-8", newline="") as output:
                csv.writer(output, delimiter=delimiter).writerows(
                    [self.header, *self.data]
                )
        elif suffix == ".xls":
            workbook = xlwt.Workbook()
            sheet = workbook.add_sheet("table")
            for row_index, row in enumerate([self.header, *self.data]):
                for column_index, value in enumerate(row):
                    sheet.write(row_index, column_index, value)
            workbook.save(str(target))
        else:
            raise ValueError(f"Unsupported table format: {suffix or '<none>'}")
        self.filename = target

    def get_column(
        self,
        column: int,
        *,
        unique: bool = False,
    ) -> Iterator[CellValue]:
        """Yield one column, optionally removing repeated values."""
        previous: list[CellValue] = []
        for row in self.data:
            value = row[column]
            if not unique or value not in previous:
                yield value
                previous.append(value)

    def __len__(self) -> int:
        return len(self.data)
