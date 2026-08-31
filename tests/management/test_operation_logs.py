"""Tests for safe bounded operation-log display."""

from __future__ import annotations

from pathlib import Path

import pytest
from django.test import override_settings

from publication_management.logs import read_recent_operation_log
from publication_management.operation_store import enqueue_publication_operation
from stringprint2.services.publication_operations import ProcessPublicationRequest


@pytest.mark.django_db
def test_log_reader_rejects_paths_outside_operation_log_root(
    org,
    tmp_path: Path,
) -> None:
    """A stored path cannot turn the authenticated UI into an arbitrary reader."""
    operation = enqueue_publication_operation(
        ProcessPublicationRequest(
            organisation_slug=org.slug,
            publication_slug="minimal-doc",
        ),
        org,
        request_source="test",
    )
    secret = tmp_path / "secret.txt"
    secret.write_text("not public")
    operation.log_path = str(secret)

    with override_settings(MEDIA_ROOT=tmp_path / "media"):
        assert read_recent_operation_log(operation) == "Log file is unavailable."


@pytest.mark.django_db
def test_log_reader_returns_only_the_most_recent_lines(org, tmp_path: Path) -> None:
    """Large worker logs do not produce unbounded operation-detail responses."""
    operation = enqueue_publication_operation(
        ProcessPublicationRequest(
            organisation_slug=org.slug,
            publication_slug="minimal-doc",
        ),
        org,
        request_source="test",
    )
    log_root = tmp_path / "operation_logs"
    log_root.mkdir()
    log_path = log_root / "operation.log"
    log_path.write_text("\n".join(f"line {number}" for number in range(250)))
    operation.log_path = str(log_path)

    with override_settings(MEDIA_ROOT=tmp_path):
        recent = read_recent_operation_log(operation).splitlines()

    assert len(recent) == 200
    assert recent[0] == "line 50"
    assert recent[-1] == "line 249"
