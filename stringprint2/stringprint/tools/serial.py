from django.db import models
import json
import pickle


def register_for_serial(cls):
    """
    decorator that allows classes to be serialsed into jsonblocks
    """

    BasicSerial.classes[cls.__name__] = cls
    return cls


class BasicSerial(object):
    """
    very basic recursive object serialiser
    """

    allowed = [str, str, int, float]
    classes = {}

    @classmethod
    def loads(cls, obj):
        di = json.loads(obj)
        return cls.restore_object(di)

    @classmethod
    def dumps(cls, obj):
        di = cls.convert_object(obj)
        return json.dumps(di)

    @classmethod
    def convert_object(cls, obj):
        """
        convert all objects to dictionaries - otherwise preserve structure
        """

        if obj == None:
            return obj

        for a in cls.allowed:
            if isinstance(obj, a):
                return obj

        if isinstance(obj, list):
            return [cls.convert_object(x) for x in obj]

        if isinstance(obj, dict):
            return {x: cls.convert_object(y) for x, y in obj.items()}

        # all other objects

        return {
            "_type": obj.__class__.__name__,
            "_content": cls.convert_object(obj.__dict__),
        }

    @classmethod
    def restore_object(cls, obj):
        """
        recreate objects bases on classes currently avaliable
        """

        if obj == None:
            return obj

        for a in cls.allowed:
            if isinstance(obj, a):
                return obj

        if isinstance(obj, list):
            return [cls.restore_object(x) for x in obj]

        if isinstance(obj, dict):
            try:
                # object restoration
                t = obj["_type"]

                model = cls.classes[t]

                ins = model.__new__(model)
                ins.__dict__.update(
                    {x: cls.restore_object(y) for x, y in obj["_content"].items()}
                )

                return ins
            except KeyError:
                return {x: cls.restore_object(y) for x, y in obj.items()}


class JsonBlockField(models.TextField):
    """
    store a collection of generic objects in JSON database
    """

    def from_db_value(self, value, expression, connection, context):
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
