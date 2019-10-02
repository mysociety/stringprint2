# -*- coding: utf-8 -*-
'''
Created on Jul 29, 2016

@author: Alex
'''
import json
from useful_inkleby.files import QuickGrid
from django.utils.safestring import mark_safe
import random
import string
from django.template.loader import render_to_string
from django.template.loader import get_template
from charts.chart_config import ChartType
from useful_inkleby.useful_django.serialisers.basic_json import SerialObject


RENDER_TABLES_AS_CHARTS = False

def id_generator(size=6, chars=string.ascii_uppercase):
    return ''.join(random.choice(chars) for _ in range(size))


class ChartCollection(object):
    """
    a chart collection lets you combine the render functions for multiple tables
    """

    def __init__(self, charts):
        
        if RENDER_TABLES_AS_CHARTS is False:
            charts = [x for x in charts if x.chart_type != "table_chart"]
        self.charts = charts
        self.make_static = False
        self.packages = set([x.package_name() for x in self.charts])


    def render_packages(self):
        return mark_safe(json.dumps(list(self.packages)))

    def render_chart_code(self):

        for c in self.charts:
            if self.make_static:
                c.make_static = True
            else:
                c.make_static = False
        if self.charts:
            c = {'collection': self}
            template = get_template("charts//set_code.html")
            return mark_safe(template.render(c))
        else:
            return ""


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
        if self.name.lower().strip() in ["%", "percent", "percentage"] and self.format == "":
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


class GoogleChart(SerialObject):
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
        self.set_local_options()

        if file_name:
            self.load_from_file(file_name)

    def change_chart_type(self, chart_type):
        self.chart_type = chart_type
        self.set_local_options()

    def set_local_options(self):
        if self.get_config().options:
            self.options = self.get_config().options()
        else:
            self.options = {}

    def get_config(self):
        # not stored in object so we can seralise and update elsewhere
        return ChartType.registered[self.chart_type]

    def package_name(self):
        return self.get_config().package_name

    def google_type(self):
        return self.get_config().google_type

    def code_template(self):
        return self.get_config().code_template

    def compile_options(self):

        if self.options:
            if isinstance(self.options, dict):
                return self.options
            else:
                return self.options.get_options()
        else:
            return {}

    def json_options(self):
        return mark_safe(json.dumps(self.compile_options()))

    def render_div(self, caption):
        extra_rows = 2
        if len(self.columns) > 5:
            multiple = 24.5
        else:
            multiple = 24.5
        self.row_height = (multiple * (len(self.rows)+extra_rows)) + 5
        self.caption = caption
        rendered = render_to_string('charts//google_charts_div.html', {"chart": self})
        return mark_safe(rendered)

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
                col_type = 'string'
            self.add_column(name=col_name,
                            type=col_type,
                            setting=setting)

        self.rows = qg.data
        return self

    def add_column(self, *args, **kwargs):
        column = Column(*args, **kwargs)
        self.columns.append(column)

    def add_row(self, row):
        assert len(row) == len(self.columns)
        self.rows.append(row)

    def render_code(self):
        c = {'chart': self}
        template = get_template(self.code_template())
        return mark_safe(template.render(c))

    def render_data(self):
        table = []
        l = len(self.rows)
        for rx, r in enumerate(self.rows):
            row = [self.columns[i].format_value(
                x, rx, l) for i, x in enumerate(r)]
            table.append(row)

        return mark_safe(json.dumps(table))

    def render_bootstrap_table(self, caption):
        """
        makes a plain, boring html table of the data
        """
        header = [x.name for x in self.columns]
        rows = []

        for r in self.rows:
            row = [self.columns[i].boring_format(x) for i, x in enumerate(r)]
            rows.append(row)

        context = {"header": header,
                   "rows": rows,
                   "caption": caption}

        rendered = render_to_string('charts//bootstrap_table.html', context)
        return mark_safe(rendered)

    def render_html_table(self, caption):
        """
        makes a plain, boring html table of the data
        """
        header = [x.name for x in self.columns]
        rows = []

        for r in self.rows:
            row = [self.columns[i].boring_format(x) for i, x in enumerate(r)]
            rows.append(row)

        context = {"header": header,
                   "rows": rows,
                   "caption": caption}

        rendered = render_to_string('charts//basic_table.html', context)

        return mark_safe(rendered)
