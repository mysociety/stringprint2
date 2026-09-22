"""
Parse document selections supplied to interactive CLI commands.
"""

from __future__ import annotations

from enum import StrEnum
from typing import NamedTuple


class DocumentSelectionScope(StrEnum):
    """
    Describe which publications an interactive command targets.
    """

    CURRENT = "current"
    ALL = "all"
    NAMED = "named"


class DocumentSelection(NamedTuple):
    """
    Hold parsed publication targets and command options.
    """

    scope: DocumentSelectionScope
    slugs: tuple[str, ...]
    options: tuple[str, ...]

    @property
    def option_text(self) -> str:
        """
        Return options in the legacy command-handler representation.
        """

        return " ".join(self.options)


def parse_document_selection(value: str) -> DocumentSelection:
    """
    Parse the document names and supported modifiers from command input.
    """

    tokens = tuple(token for token in value.strip().lower().split(" ") if token)
    options = tuple(token for token in tokens if token == "refresh" or "no-" in token)
    slugs = tuple(token for token in tokens if token not in options)
    if not slugs:
        scope = DocumentSelectionScope.CURRENT
    elif "all" in slugs:
        scope = DocumentSelectionScope.ALL
        slugs = ()
    else:
        scope = DocumentSelectionScope.NAMED
    return DocumentSelection(scope=scope, slugs=slugs, options=options)
