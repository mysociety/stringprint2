"""
End-to-end gate: every fixture document loads and processes.

If this fails, nothing else in the suite is meaningful.
"""

from __future__ import annotations

import pytest

SLUGS = ["minimal-doc", "kitchen-sink", "legacy-doc", "multipage-doc"]


@pytest.mark.django_db
@pytest.mark.parametrize("slug", SLUGS)
def test_document_processes(process_doc, slug: str) -> None:
    article = process_doc(slug)
    version = article.content()

    assert version.raw, "no source text loaded"
    assert len(version.sections) >= 1
    assert all(section.name for section in version.sections)
