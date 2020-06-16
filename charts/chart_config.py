'''
Created on 1 Aug 2016

@author: alex
'''


from .options.chart_options import LineChartOption
from useful_inkleby.useful_django.serialisers import SerialBase


class ChartType(SerialBase):

    registered = {}

    def __init__(self, chart_type, code_template, package_name="corechart", options=None, google_type=None):

        self.chart_type = chart_type
        self.package_name = package_name
        self.code_template = code_template
        self.options = options
        self.google_type = google_type
        self.__class__.registered[self.chart_type] = self


ChartType("line_chart", "charts//line_code.html",
          options=LineChartOption, google_type="LineChart")
ChartType("table_chart", "charts//table_code.html", package_name="table")
