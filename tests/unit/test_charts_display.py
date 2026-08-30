"""
charts.display - the table/chart layer.

Column is pure. Chart.load_from_file reads a spreadsheet, and the two render
methods go through Django templates, so those need settings but no database.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from stringprint2.charts import Chart
from stringprint2.charts.display import (
    RENDER_TABLES_AS_CHARTS,
    ChartCollection,
    Column,
    id_generator,
    safe_markdown,
)

TABLE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "doc_source"
    / "_docs"
    / "kitchen-sink"
    / "assets"
    / "table-one.xls"
)


class TestColumnConstruction:
    @pytest.mark.parametrize("name", ["%", "percent", "percentage", "Percent", " % "])
    def test_percentage_names_get_a_percent_format(self, name: str) -> None:
        column = Column(name=name)
        assert column.format == "{0:.0f}%"
        assert column.multiple == 100

    def test_an_explicit_format_suppresses_percent_detection(self) -> None:
        column = Column(name="%", format="{0:.2f}")
        assert column.format == "{0:.2f}"
        assert column.multiple == 1

    def test_currency_marker_is_stripped_and_sets_the_format(self) -> None:
        column = Column(name="Cost [[currency]]")
        assert column.name == "Cost"
        assert column.format == "£{:20,.0f}"

    def test_an_ordinary_name_is_left_alone(self) -> None:
        column = Column(name="Region")
        assert (column.name, column.format, column.multiple) == ("Region", "", 1)


class TestColumnFormatting:
    def test_adjust_func_applies_the_multiple(self) -> None:
        assert Column(name="%").adjust_func(0.5) == 50.0

    def test_boring_format_leaves_strings_alone(self) -> None:
        assert Column(name="Year", type="string").boring_format("2019") == "2019"

    def test_boring_format_applies_a_number_format(self) -> None:
        # 0.125 * 100 = 12.5, and format() rounds half to even
        column = Column(name="%", type="number")
        assert column.boring_format(0.125) == "12%"
        assert column.boring_format(0.33) == "33%"

    def test_boring_format_without_a_format_stringifies(self) -> None:
        assert Column(name="n", type="number").boring_format(7) == "7"

    def test_format_value_returns_value_and_display(self) -> None:
        column = Column(name="%", type="number")
        assert column.format_value(0.125, 0, 1) == {"v": 0.125, "f": "12%"}

    def test_format_value_lowercases_the_sort_key_for_strings(self) -> None:
        column = Column(name="Region", type="string")
        assert column.format_value("North", 0, 1) == {"v": "north", "f": "North"}

    def test_format_value_stringifies_non_strings_in_a_string_column(self) -> None:
        column = Column(name="Region", type="string")
        assert column.format_value(12, 0, 1) == {"v": "12", "f": "12"}

    def test_split_setting_sorts_on_the_leading_number(self) -> None:
        column = Column(name="Region", setting="split[")
        assert column.format_value("12[north]", 0, 1) == {"v": 12.0, "f": "12[north]"}


class TestChartLoadFromFile:
    @pytest.fixture(scope="class")
    def chart(self) -> Chart:
        return Chart(chart_type="table_chart", file_name=str(TABLE))

    def test_column_names_come_from_the_header_row(self, chart: Chart) -> None:
        assert [c.name for c in chart.columns] == ["Year", "%", "Cost", "Region"]

    def test_a_year_column_is_forced_to_string(self, chart: Chart) -> None:
        assert chart.columns[0].type == "string"

    def test_numeric_columns_are_detected(self, chart: Chart) -> None:
        assert chart.columns[1].type == "number"
        assert chart.columns[2].type == "number"

    def test_the_split_setting_is_read_off_the_header(self, chart: Chart) -> None:
        assert chart.columns[3].setting == "split["
        assert chart.columns[3].name == "Region"

    def test_rows_are_loaded(self, chart: Chart) -> None:
        assert len(chart.rows) == 4
        assert chart.rows[0][0] == "2019"

    def test_render_data_is_json_of_value_and_display_pairs(self, chart: Chart) -> None:
        import json

        table = json.loads(chart.render_data())
        assert len(table) == 4
        assert table[0][1] == {"v": 0.125, "f": "12%"}


class TestChartRendering:
    @pytest.fixture(scope="class")
    def chart(self) -> Chart:
        return Chart(chart_type="table_chart", file_name=str(TABLE))

    def test_html_table_has_a_header_and_a_row_per_record(self, chart: Chart) -> None:
        html = chart.render_html_table("A caption")
        assert "A caption" in html
        assert html.count("<tr") == 5
        assert "Region" in html

    def test_html_table_without_a_header_promotes_it_into_the_body(
        self, chart: Chart
    ) -> None:
        html = chart.render_html_table("", no_header=True)
        assert "<th" not in html
        assert html.count("<tr") == 5

    def test_cell_values_are_markdown_rendered(self, chart: Chart) -> None:
        assert "<p>" in chart.render_html_table("")

    def test_bootstrap_table_renders(self, chart: Chart) -> None:
        html = chart.render_bootstrap_table("A caption")
        assert "A caption" in html
        assert "Region" in html

    def test_bootstrap_no_header_inserts_once_per_row(self, chart: Chart) -> None:
        """
        Known defect: in render_bootstrap_table the `if no_header` block sits
        inside the row loop, so it runs once per row - inserting the header
        first and then an empty list for every subsequent row. The equivalent
        block in render_html_table is correctly outside the loop.

        Pinned rather than fixed; see docs/feature-inventory.md.
        """
        html = chart.render_bootstrap_table("", no_header=True)
        rows = html.count("<tr")
        assert rows == 8, "expected 4 data rows + 1 header + 3 empty rows"


class TestChartCollection:
    def test_table_charts_are_filtered_out(self) -> None:
        assert RENDER_TABLES_AS_CHARTS is False
        collection = ChartCollection([Chart(chart_type="table_chart")])
        assert collection.charts == []

    def test_a_non_table_chart_cannot_be_collected(self) -> None:
        """
        Known defect: ChartCollection.__init__ calls x.package_name() on each
        surviving chart, but package_name lives on ChartType (and is a string
        there, not a method) - Chart has no such attribute. Since table charts
        are always filtered out, the collection only works when it ends up
        empty. Pinned rather than fixed; see docs/feature-inventory.md.
        """
        with pytest.raises(AttributeError, match="package_name"):
            ChartCollection([Chart(chart_type="line_chart")])

    def test_make_static_defaults_off(self) -> None:
        assert ChartCollection([]).make_static is False


class TestHelpers:
    def test_safe_markdown_only_touches_strings(self) -> None:
        assert safe_markdown(12) == 12
        assert safe_markdown("*a*") == "<p><em>a</em></p>"

    def test_id_generator_length_and_alphabet(self) -> None:
        value = id_generator(5)
        assert len(value) == 5
        assert value.isupper()
