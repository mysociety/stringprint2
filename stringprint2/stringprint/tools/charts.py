"""
Created on Jul 29, 2016

@author: Alex
"""
import json
from useful_inkleby.files import QuickGrid
from django.utils.safestring import mark_safe
import random
import string
from django.template import Template, Context
from django.template.loader import get_template


def id_generator(size=6, chars=string.ascii_uppercase):
    return "".join(random.choice(chars) for _ in range(size))


class ChartCollection(object):
    def __init__(self, charts):
        self.charts = charts
        self.packages = set([x.__class__.package_name for x in self.charts])

    def render_packages(self):
        return mark_safe(json.dumps(list(self.packages)))

    def render_code(self):
        c = Context({"collection": self})
        template = get_template("charts//set_code.html")
        return mark_safe(template.render(c))


class Column(object):
    def __init__(self, name="", type="string", format=""):
        self.name = name
        self.type = type
        self.format = format
        self.adjust_func = lambda x: x

        if self.name.lower().strip() in ["%", "percent", "percentage"]:
            if self.format == "":
                self.format = "{0:.0f}%"
                self.adjust_func = lambda x: x * 100

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

    def format_value(self, value):
        # returns a formatted value for display
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
                return value
            else:
                return str(value)


class BaseChart(object):
    def __init__(self, name="", file_name=""):
        self.name = name
        self.columns = []
        self.rows = []
        self.ident = id_generator(5)
        if file_name:
            self.load_from_file(file_name)

    def compile_options(self):
        options = {
            "title": self.name,
        }

        return options

    def json_options(self):
        return mark_safe(json.dumps(self.compile_options()))

    def render_div(self):
        return mark_safe('<div id="{0}"></div>'.format(self.ident))

    def load_from_file(self, path):
        qg = QuickGrid().open(path)
        for x, h in enumerate(qg.header):
            col_name = h
            types = set([type(i) for i in qg.get_column(x)])
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

            self.add_column(name=col_name, type=col_type)

        self.rows = qg.data
        return self

    def add_column(self, *args, **kwargs):
        column = Column(*args, **kwargs)
        self.columns.append(column)

    def add_row(self, row):
        assert len(row) == len(self.columns)
        self.rows.append(row)

    def render_code(self):
        c = Context({"chart": self})
        template = get_template(self.__class__.code_template)
        return mark_safe(template.render(c))

    def render_data(self):
        table = []
        for r in self.rows:
            row = [self.columns[i].format_value(x) for i, x in enumerate(r)]
            table.append(row)

        return mark_safe(json.dumps(table))


class LineChartOptions(object):
    def __init__(self):
        pass


class GoogleLineChart(BaseChart):
    package_name = "corechart"
    code_template = "charts//line_code.html"

    def compile_options(self):
        base = super(GoogleLineChart, self).compile_options()

        options = {
            "curveType": "function",
            "legend": {"position": "bottom"},
            "smoothLine": True,
        }

        options.update(base)

        return options


class GoogleTable(BaseChart):
    package_name = "table"
    code_template = "charts//table_code.html"

    def render_html_table(self):
        """
        makes a plain, boring html table
        """
        table_format = "<table>{0}</table>"
        header_format = "<th>{0}</th>"
        cell_format = "<td>{0}</td>"
        row_format = "<tr>{0}</tr>"

        header = "".join([header_format.format(x.name) for x in self.columns])
        header = row_format.format(header)
        formatted = header
        for r in self.rows:
            row = [self.columns[i].boring_format(x) for i, x in enumerate(r)]
            row = [cell_format.format(x) for x in row]
            row = row_format.format("".join(row))
            formatted += row

        return mark_safe(table_format.format(formatted))
