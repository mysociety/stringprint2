"""Tests for durable publication operation records."""

from __future__ import annotations

import pytest

from publication_management.models import (
    PublicationOperation,
    PublicationOperationState,
)
from stringprint2.services.publication_operations import ProcessPublicationRequest


@pytest.mark.django_db
def test_operation_persists_a_versioned_typed_request(org) -> None:
    """A queued request retains its identity and validated parameters."""
    request = ProcessPublicationRequest(
        organisation_slug=org.slug,
        publication_slug="minimal-doc",
        refresh_header=False,
        preprocess=False,
    )

    operation = PublicationOperation.objects.create(
        organisation=org,
        publication_slug=request.publication_slug,
        operation_name=request.operation,
        parameters=request.model_dump(mode="json"),
        request_source="test",
    )

    operation.refresh_from_db()
    assert operation.state == PublicationOperationState.PENDING
    assert operation.schema_version == 1
    assert operation.parameters["operation"] == "process"
    assert operation.parameters["refresh_header"] is False
    assert str(operation) == "process: minimal-doc (pending)"
