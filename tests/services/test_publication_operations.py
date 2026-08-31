"""Tests for typed publication operation dispatch."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from stringprint2.services.publication_operations import (
    ProcessPublicationRequest,
    ProcessPublicationResult,
    PublicationOperationStage,
    RenderPublicationRequest,
    RenderPublicationResult,
    run_publication_operation,
    validate_publication_operation,
)
from stringprint2.services.publication_rendering import PublicationRenderFormat


class FakePublication:
    """Record publication service calls made by operation handlers."""

    title = "Managed publication"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def load_from_yaml(self, storage_dir: Path, refresh_header: bool = False) -> None:
        self.calls.append(f"load:{refresh_header}")

    def import_assets(self, asset_folder: Path, refresh: bool) -> None:
        self.calls.append(f"assets:{asset_folder.name}:{refresh}")

    def load_from_file(self) -> None:
        self.calls.append("source")

    def process(self) -> None:
        self.calls.append("process")

    def run_command(self, command: str) -> None:
        self.calls.append(f"command:{command}")

    def render(self, destination: Path, refresh_all: bool = False) -> None:
        self.calls.append(f"web:{destination}:{refresh_all}")

    def create_ebook(self, destination: Path) -> None:
        self.calls.append(f"epub:{destination}")

    def create_kindle(self, destination: Path) -> None:
        self.calls.append(f"kindle:{destination}")


class RecordingProgress:
    """Collect progress stages for assertions."""

    def __init__(self) -> None:
        self.updates: list[tuple[PublicationOperationStage, str]] = []

    def update(self, stage: PublicationOperationStage, detail: str = "") -> None:
        """Record one stage update."""
        self.updates.append((stage, detail))


def test_process_operation_delegates_with_validated_options(tmp_path: Path) -> None:
    """The process handler invokes the existing workflow and reports stages."""
    publication = FakePublication()
    progress = RecordingProgress()
    request = ProcessPublicationRequest(
        organisation_slug="default",
        publication_slug="example",
        refresh_header=False,
        preprocess=False,
    )
    result = run_publication_operation(
        request, publication, tmp_path, tmp_path / "published", progress
    )

    assert result == ProcessPublicationResult(title="Managed publication")
    assert publication.calls == [
        "load:False",
        "assets:assets:False",
        "source",
        "process",
    ]
    assert progress.updates == [
        (PublicationOperationStage.STARTING, "example"),
        (PublicationOperationStage.PROCESSING, "example"),
        (PublicationOperationStage.COMPLETE, "example"),
    ]


def test_render_operation_returns_the_generated_artefact(tmp_path: Path) -> None:
    """The render handler preserves output format, destination, and options."""
    publication = FakePublication()
    destination = tmp_path / "published" / "example"
    request = RenderPublicationRequest(
        organisation_slug="default",
        publication_slug="example",
        output_format=PublicationRenderFormat.WEB,
        refresh=True,
    )
    result = run_publication_operation(request, publication, tmp_path, destination)

    assert result == RenderPublicationResult(
        destination=destination,
        output_format=PublicationRenderFormat.WEB,
    )
    assert publication.calls == [f"web:{destination}:True"]


def test_serialized_requests_use_a_discriminated_schema() -> None:
    """Queued JSON is restored to the request model selected by operation name."""
    request = validate_publication_operation(
        {
            "operation": "render",
            "organisation_slug": "default",
            "publication_slug": "example",
            "output_format": "epub",
        }
    )

    assert isinstance(request, RenderPublicationRequest)
    assert request.output_format is PublicationRenderFormat.EPUB


def test_unknown_operations_are_rejected_during_validation() -> None:
    """Unregistered callables or arbitrary commands cannot enter the runner."""
    with pytest.raises(ValidationError):
        validate_publication_operation(
            {
                "operation": "run_anything",
                "organisation_slug": "default",
                "publication_slug": "example",
            }
        )
