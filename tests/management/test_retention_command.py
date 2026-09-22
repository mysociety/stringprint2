"""Tests for the publication operation retention command."""

from __future__ import annotations

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from publication_management.models import (
    PublicationOperation,
    PublicationOperationState,
)


@pytest.mark.django_db
def test_retention_command_supports_a_non_destructive_dry_run(org, tmp_path) -> None:
    """The operational command reports its scope without deleting by default flag."""
    operation = PublicationOperation.objects.create(
        organisation=org,
        publication_slug="minimal-doc",
        operation_name="process",
        parameters={},
        state=PublicationOperationState.FAILED,
        finished_at=timezone.now() - timedelta(days=100),
        request_source="test",
    )
    output = StringIO()

    with override_settings(MEDIA_ROOT=tmp_path):
        call_command(
            "prune_publication_operations",
            older_than_days=90,
            dry_run=True,
            stdout=output,
        )

    assert "Would prune 1 operation(s)" in output.getvalue()
    assert PublicationOperation.objects.filter(pk=operation.pk).exists()
