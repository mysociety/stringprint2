"""Tests for the project-owned object serializer."""

from __future__ import annotations

import json

import pytest

from stringprint2.serialization import ObjectSerializer, SerialObject


class ExampleValue(SerialObject):
    """Small serializable value used to exercise nested restoration."""

    def __init__(self, label: str) -> None:
        self.label = label


def test_registered_objects_round_trip_in_nested_data() -> None:
    """The serializer preserves the useful_inkleby JSON representation."""
    original = {"items": [ExampleValue("first")], "enabled": True}

    serialized = ObjectSerializer.dumps(original)
    restored = ObjectSerializer.loads(serialized)

    assert json.loads(serialized) == {
        "items": [
            {"_type": "ExampleValue", "_content": {"label": "first"}},
        ],
        "enabled": True,
    }
    assert isinstance(restored["items"][0], ExampleValue)
    assert restored["items"][0].label == "first"


def test_unknown_persisted_types_fail_clearly() -> None:
    """Corrupt or unavailable object types do not silently become dictionaries."""
    serialized = '{"_type": "MissingType", "_content": {}}'

    with pytest.raises(ValueError, match="Unknown serialized object type: MissingType"):
        ObjectSerializer.loads(serialized)


def test_unsupported_runtime_values_are_rejected() -> None:
    """Only deliberately supported JSON values and registered objects are stored."""
    with pytest.raises(TypeError, match="Cannot serialize set"):
        ObjectSerializer.dumps({1, 2})
