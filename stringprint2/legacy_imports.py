"""Compatibility aliases for preprocessors using pre-package app names.

Internal imports use stringprint2.*. Aliases resolve to the very same modules,
so historical extensions cannot register a second copy of a Django model.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import sys
from types import ModuleType
from typing import Any

LEGACY_APPS = frozenset(
    {"stringprint", "frontend", "charts", "proj", "publication_management"}
)


class _LegacyAppLoader(importlib.abc.Loader):
    def create_module(self, spec: Any) -> ModuleType:
        return importlib.import_module("stringprint2." + spec.name)

    def exec_module(self, module: ModuleType) -> None:
        # The canonical import already executed this module.
        pass


class _LegacyAppFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname: str, path: Any = None, target: Any = None) -> Any:
        if fullname.split(".", 1)[0] not in LEGACY_APPS:
            return None
        canonical = importlib.util.find_spec("stringprint2." + fullname)
        if canonical is None:
            return None
        return importlib.util.spec_from_loader(
            fullname,
            _LegacyAppLoader(),
            is_package=canonical.submodule_search_locations is not None,
        )


def install_legacy_aliases() -> None:
    if not any(isinstance(finder, _LegacyAppFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, _LegacyAppFinder())
