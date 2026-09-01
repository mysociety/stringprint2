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


def test_word_table_can_be_saved_as_xlsx(tmp_path) -> None:
    """Word table values survive an XLSX round trip."""
    path = tmp_path / "table.xlsx"

    DataTable(
        ["label", "value", "enabled", "notes", "empty"],
        [["Café", 1, True, "First line\nSecond line", None]],
    ).save(path)
    loaded = DataTable().open(path)

    assert loaded.header == ["label", "value", "enabled", "notes", "empty"]
    assert loaded.data == [["Café", 1, True, "First line\nSecond line", None]]
