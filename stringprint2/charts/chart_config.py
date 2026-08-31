"""
Define the available chart types and their rendering configuration.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import ClassVar

from useful_inkleby.useful_django.serialisers import SerialBase


class ChartType(SerialBase):
    """
    Describe and register a chart renderer.
    """

    registered: ClassVar[dict[str, ChartType]] = {}

    def __init__(
        self,
        chart_type: str,
        code_template: str,
        package_name: str = "corechart",
        options: Mapping[str, object] | None = None,
    ) -> None:
        self.chart_type = chart_type
        self.package_name = package_name
        self.code_template = code_template
        self.options = options
        self.__class__.registered[self.chart_type] = self


ChartType("table_chart", "charts//table_code.html", package_name="table")
