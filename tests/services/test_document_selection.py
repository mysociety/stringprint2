"""
Contract tests for interactive CLI document selection.
"""

from stringprint2.services.document_selection import (
    DocumentSelection,
    DocumentSelectionScope,
    parse_document_selection,
)


def test_empty_selection_uses_current_document() -> None:
    assert parse_document_selection("") == DocumentSelection(
        scope=DocumentSelectionScope.CURRENT,
        slugs=(),
        options=(),
    )


def test_named_documents_are_normalised() -> None:
    assert parse_document_selection(
        " First-Report second-report "
    ) == DocumentSelection(
        scope=DocumentSelectionScope.NAMED,
        slugs=("first-report", "second-report"),
        options=(),
    )


def test_all_selection_discards_other_document_names() -> None:
    assert parse_document_selection("first-report all") == DocumentSelection(
        scope=DocumentSelectionScope.ALL,
        slugs=(),
        options=(),
    )


def test_modifiers_are_passed_separately_from_document_names() -> None:
    selection = parse_document_selection(
        "first-report refresh --no-preprocess --no-refresh"
    )

    assert selection.slugs == ("first-report",)
    assert selection.options == ("refresh", "--no-preprocess", "--no-refresh")
    assert selection.option_text == "refresh --no-preprocess --no-refresh"
