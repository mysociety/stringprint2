"""Compatibility access to authored options without injecting model attributes."""

from __future__ import annotations

from typing import Any, ClassVar


class ConfiguredModelValues:
    """Keep custom options in extra_values, with explicit legacy field overrides.

    Templates historically read custom options as model attributes. Missing
    attributes still resolve there, while model methods and internal state are
    never replaced by arbitrary configuration keys.
    """

    configuration_fields: ClassVar[frozenset[str]] = frozenset()
    extra_values: Any

    def __getattr__(self, name: str) -> Any:
        if not name.startswith("_") and name != "extra_values":
            if "_state" in self.__dict__:
                values = self.extra_values
                if isinstance(values, dict) and name in values:
                    return values[name]
        raise AttributeError(f"{type(self).__name__!s} has no attribute {name!r}")

    def apply_configuration_field_overrides(self) -> None:
        """Preserve historical authored values stored outside their model fields."""
        values = self.__dict__.get("extra_values", {})
        if isinstance(values, dict):
            for name in self.configuration_fields & values.keys():
                setattr(self, name, values[name])
