from __future__ import absolute_import

from django.db import models

try:
    from useful_inkleby.useful_django.serialisers import BasicSerial
except:
    from ..serialisers import BasicSerial


class JsonBlockField(models.TextField):
    """
    store a collection of generic objects in a jsonblock. 
    Useful for when you have a hierarchy of classes that are only accessed
    from the one object. 
    """

    def from_db_value(self, value, expression, connection):
        if value is None:
            return []
        return BasicSerial.loads(value)

    def to_python(self, value):
        if isinstance(value, list):
            return value

        if value is None:
            return value

        return BasicSerial.loads(value)

    def get_prep_value(self, value):
        return BasicSerial.dumps(value)
