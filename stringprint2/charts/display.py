# -*- coding: utf-8 -*-

import json
from useful_inkleby.files import QuickGrid
from django.utils.safestring import mark_safe
import random
import string
from django.template.loader import render_to_string
from useful_inkleby.useful_django.serialisers.basic_json import SerialObject
import markdown
from typing import Any, List

RENDER_TABLES_AS_CHARTS = False


def safe_markdown(x):
    if isinstance(x, str):
        return markdown.markdown(x)
    return x


def id_generator(size=6, chars=string.ascii_uppercase):
    return "".join(random.choice(chars) for _ in range(size))


class ChartCollection(object):
    """
    a chart collection lets you combine the render functions for multiple tables
    """

    def __init__(self, charts: List[Any]) -> None:

        if RENDER_TABLES_AS_CHARTS is False:
            charts = [x for x in charts if x.chart_type != "table_chart"]
        self.charts = charts
        self.make_static = False
        self.packages = set([x.package_name() for x in self.charts])


class Column(SerialObject):
    """
    stores settings related to a datatable column
    """

    def __init__(self, name="", type="string", format="", setting=None, multiple=1):
        self.name = name
        self.type = type
        self.format = format
        self.setting = setting
        self.multiple = multiple
        if (
            self.name.lower().strip() in ["%", "percent", "percentage"]
            and self.format == ""
        ):
            self.format = "{0:.0f}%"
            self.multiple = 100
        if "[[currency]]" in self.name:
            self.name = self.name.replace("[[currency]]", "").strip()
            self.format = "£{:20,.0f}"

    def adjust_func(self, value):
        return value * self.multiple

    def boring_format(self, value):
        # returns a formatted value for display
        if self.type == "number":
            if self.format:
                nvalue = self.adjust_func(value)
                self.format.format(nvalue)
                formatted = self.format.format(nvalue)
            else:
                formatted = str(value)

            return formatted

        else:
            return value

    def format_value(self, value, row, total):
        di = self._format_value(value, row)
        return di

    def _format_value(self, value, row):
        # returns a formatted value for display
        if self.setting == "split[":
            nvalue = float(value.split("[")[0].strip())
            formatted = value
            return {"v": nvalue, "f": formatted}
        if self.type == "number":
            if self.format:
                nvalue = self.adjust_func(value)
                self.format.format(nvalue)
                formatted = self.format.format(nvalue)
            else:
                formatted = str(value)

            return {"v": value, "f": formatted}

        else:
            if isinstance(value, str):
                return {"v": value.lower(), "f": value}
            else:
                return {"v": str(value).lower(), "f": str(value)}


class Chart(SerialObject):
    """
    stores the configuration and data for a chart - renders charts
    to be passed to the ChartCollection for final work.
    """

    def __init__(self, name="", file_name="", chart_type="line_chart"):

        self.chart_type = chart_type
        self.name = name
        self.filename = file_name
        self.columns = []
        self.rows = []
        self.ident = id_generator(5)

        if file_name:
            self.load_from_file(file_name)

    def load_from_file(self, path):
        qg = QuickGrid().open(path)
        for x, h in enumerate(qg.header):
            col_name = h
            setting = None
            if col_name and "||" in col_name:
                col_name, setting = col_name.split("||")

            if col_name is None:
                col_name = ""

            values = qg.get_column(x)
            if setting == "split[":
                values = [float(x.split("[")[0]) for x in values]

            types = set([type(i) for i in values])
            types = list(types)
            if len(types) > 1:
                col_type = "string"
            else:
                t = types[0]
                if t in [float, int]:
                    col_type = "number"
                elif t in ["boolean"]:
                    col_type = "boolean"
                else:
                    col_type = "string"

            if col_name.lower() == "year":
                col_type = "string"
            self.add_column(name=col_name, type=col_type, setting=setting)

        self.rows = qg.data
        return self

    def add_column(self, *args, **kwargs):
        column = Column(*args, **kwargs)
        self.columns.append(column)

    def add_row(self, row):
        assert len(row) == len(self.columns)
        self.rows.append(row)

    def render_data(self):
        table = []
        l = len(self.rows)
        for rx, r in enumerate(self.rows):
            row = [self.columns[i].format_value(x, rx, l) for i, x in enumerate(r)]
            table.append(row)

        return mark_safe(json.dumps(table))

    def render_bootstrap_table(self, caption, no_header=False):
        """
        makes a bootstrap table of the data
        """
        header = [x.name for x in self.columns]
        rows = []

        for r in self.rows:
            row = [
                mark_safe(safe_markdown(self.columns[i].boring_format(x)))
                for i, x in enumerate(r)
            ]
            rows.append(row)

            if no_header:
                rows.insert(0, header)
                header = []

        context = {"header": header, "rows": rows, "caption": caption}

        rendered = render_to_string("charts//bootstrap_table.html", context)
        return mark_safe(rendered)

    def render_html_table(self, caption, no_header=False):
        """
        makes a plain, boring html table of the data
        """
        header = [x.name for x in self.columns]
        rows = []

        for r in self.rows:
            row = [
                mark_safe(safe_markdown(self.columns[i].boring_format(x)))
                for i, x in enumerate(r)
            ]
            rows.append(row)

        if no_header:
            rows.insert(0, header)
            header = []

        context = {"header": header, "rows": rows, "caption": caption}

        rendered = render_to_string("charts//basic_table.html", context)

        return mark_safe(rendered)
