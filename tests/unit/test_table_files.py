"""Tests for the focused tabular file adapter."""

from __future__ import annotations

from stringprint2.table_files import DataTable


def test_csv_round_trip(tmp_path) -> None:
    """CSV headers and rows survive save and reload."""
    path = tmp_path / "chart.csv"
    table = DataTable(["year", "value"], [[2025, 12], [2026, 15]])

    table.save(path)
    loaded = DataTable().open(path)

    assert loaded.header == ["year", "value"]
    assert loaded.data == [["2025", "12"], ["2026", "15"]]
    assert list(loaded.get_column(1)) == ["12", "15"]


def test_word_table_can_be_saved_as_xls(tmp_path) -> None:
    """The Word extraction path can still emit legacy XLS assets."""
    path = tmp_path / "table.xls"

    DataTable(["label", "value"], [["A", 1]]).save(path)
    loaded = DataTable().open(path)

    assert loaded.header == ["label", "value"]
    assert loaded.data == [["A", 1.0]]
