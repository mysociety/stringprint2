"""Tests for the typed publication management dashboard."""

from __future__ import annotations

import pytest

from publication_management.dashboard import (
    build_publication_dashboard,
    publication_source_exists,
)
from publication_management.operation_store import enqueue_publication_operation
from stringprint.models import Article
from stringprint2.services.publication_operations import ProcessPublicationRequest


@pytest.mark.django_db
def test_dashboard_combines_source_load_freshness_and_latest_operation(
    org,
    monkeypatch,
) -> None:
    """One typed row gives the web page all management state for a source."""
    article, _ = Article.objects.get_or_create(
        org=org,
        slug="minimal-doc",
        defaults={"title": "Loaded minimal report"},
    )
    enqueue_publication_operation(
        ProcessPublicationRequest(
            organisation_slug=org.slug,
            publication_slug=article.slug,
        ),
        org,
        article=article,
        request_source="test",
    )
    monkeypatch.setattr(
        "publication_management.dashboard.publication_needs_update",
        lambda folder, config: folder.name == "minimal-doc",
    )

    entries = build_publication_dashboard(org)
    by_slug = {entry.slug: entry for entry in entries}

    assert "kitchen-sink" in by_slug
    assert not by_slug["kitchen-sink"].loaded
    minimal = by_slug["minimal-doc"]
    assert minimal.loaded
    assert minimal.title == "Loaded minimal report"
    assert minimal.needs_update is True
    assert minimal.latest_operation_id is not None
    assert minimal.latest_operation_state == "pending"


@pytest.mark.django_db
def test_source_validation_rejects_unknown_and_traversal_slugs(org) -> None:
    """Initial load requests remain inside discovered publication folders."""
    assert publication_source_exists(org, "minimal-doc")
    assert not publication_source_exists(org, "missing")
    assert not publication_source_exists(org, "../_conf")
