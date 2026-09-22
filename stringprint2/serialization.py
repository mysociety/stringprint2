"""
Serialize Stringprint's small object graphs into JSON-backed model fields.

The format intentionally matches the historic useful_inkleby serializer so
existing Section, Graf, Footnote, Chart, and Column values remain readable.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, ClassVar, TypeVar

from django.db import models

type JsonValue = (
    None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]
)

SerialBaseType = TypeVar("SerialBaseType", bound="SerialBase")


class ObjectSerializer:
    """Convert registered Python objects to and from the legacy JSON shape."""

    classes: ClassVar[dict[str, type[Any]]] = {}

    @classmethod
    def loads(cls, value: str) -> Any:
        """Restore an object graph from JSON text."""
        return cls.restore_object(json.loads(value))

    @classmethod
    def dumps(cls, value: object) -> str:
        """Convert an object graph to JSON text."""
        return json.dumps(cls.convert_object(value))

    @classmethod
    def convert_object(cls, value: object) -> JsonValue:
        """Convert supported values into JSON-compatible data."""
        if value is None or isinstance(value, bool | int | float | str):
            return value
        if isinstance(value, list | tuple):
            return [cls.convert_object(item) for item in value]
        if isinstance(value, Mapping):
            return {str(key): cls.convert_object(item) for key, item in value.items()}
        if isinstance(value, SerialBase):
            return value.serial_dumps()
        raise TypeError(f"Cannot serialize {type(value).__qualname__}")

    @classmethod
    def restore_object(cls, value: JsonValue) -> Any:
        """Restore registered objects recursively from JSON-compatible data."""
        if isinstance(value, list):
            return [cls.restore_object(item) for item in value]
        if isinstance(value, dict):
            object_type = value.get("_type")
            content = value.get("_content")
            if isinstance(object_type, str) and isinstance(content, dict):
                try:
                    model = cls.classes[object_type]
                except KeyError as error:
                    raise ValueError(
                        f"Unknown serialized object type: {object_type}"
                    ) from error
                return model.serial_loads(content)
            return {key: cls.restore_object(item) for key, item in value.items()}
        return value


class SerialMeta(type):
    """Register concrete serializable classes by their persisted type name."""

    def __new__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
    ) -> SerialMeta:
        model = super().__new__(cls, name, bases, namespace)
        ObjectSerializer.classes[name] = model
        return model


class SerialBase:
    """Provide the legacy dictionary-based serialization protocol."""

    @classmethod
    def serial_loads(
        cls: type[SerialBaseType], values: dict[str, JsonValue]
    ) -> SerialBaseType:
        """Construct an instance without invoking its normal initializer."""
        instance = cls.__new__(cls)
        instance.from_json(values)
        return instance

    def from_json(self, values: dict[str, JsonValue]) -> None:
        """Populate an instance from its serialized attributes."""
        self.__dict__.update(
            {
                key: ObjectSerializer.restore_object(value)
                for key, value in values.items()
            }
        )

    def serial_dumps(self) -> dict[str, JsonValue]:
        """Return the persisted representation of this instance."""
        return {
            "_type": self.__class__.__name__,
            "_content": ObjectSerializer.convert_object(self.__dict__),
        }


class SerialObject(SerialBase, metaclass=SerialMeta):
    """Base class for automatically registered serializable objects."""


class JsonBlockField(models.TextField):  # type: ignore[type-arg]
    """Store a nested object graph in a text-backed JSON column."""

    def from_db_value(
        self,
        value: str | None,
        expression: object,
        connection: object,
    ) -> Any:
        """Restore values loaded by Django's database backend."""
        if value is None:
            return []
        return ObjectSerializer.loads(value)

    def to_python(self, value: Any) -> Any:
        """Normalize values assigned by Django or application code."""
        if not isinstance(value, str):
            return value
        return ObjectSerializer.loads(value)

    def get_prep_value(self, value: object) -> str:
        """Serialize a value before writing it to the database."""
        return ObjectSerializer.dumps(value)
