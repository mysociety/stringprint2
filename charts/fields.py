from django.db import models
from useful_inkleby.useful_django.serialisers import BasicSerial
from .display import Chart


class ChartField(models.TextField):
    """
    store a collection of generic objects in a jsonblock.
    Useful for when you have a hierarchy of classes that are only accessed
    from the one object.
    """

    def __init__(self, *args, **kwargs) -> None:
        self.chart_type = None
        if "chart_type" in kwargs:
            self.chart_type = kwargs["chart_type"]
            del kwargs["chart_type"]
        super(ChartField, self).__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            if self.chart_type:
                return Chart(chart_type=self.chart_type)
            else:
                return Chart()

        return BasicSerial.loads(value)

    def to_python(self, value):
        if isinstance(value, Chart):
            return value

        if value is None:
            return value

        return BasicSerial.loads(value)

    def get_prep_value(self, value):
        return BasicSerial.dumps(value)
