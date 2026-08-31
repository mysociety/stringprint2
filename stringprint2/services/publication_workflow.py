"""Framework-neutral orchestration for publication lifecycle commands."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class PublicationDocument(Protocol):
    """Operations required from a persisted publication document."""

    title: str

    def load_from_yaml(
        self,
        storage_dir: Path,
        refresh_header: bool = False,
    ) -> None:
        """Synchronize authored configuration into the document."""
        ...

    def import_assets(self, asset_folder: Path, refresh: bool) -> None:
        """Synchronize configured assets into the document."""
        ...

    def load_from_file(self) -> None:
        """Load the authored Markdown source."""
        ...

    def process(self) -> None:
        """Compile the loaded source into its intermediate structure."""
        ...

    def run_command(self, command: str) -> None:
        """Run a configured publication command."""
        ...


class PublicationWorkflowResult(BaseModel):
    """Describe the publication affected by a completed workflow."""

    model_config = ConfigDict(frozen=True)

    title: str


def load_publication(
    document: PublicationDocument,
    folder: Path,
    *,
    refresh_header: bool = False,
) -> PublicationWorkflowResult:
    """Synchronize publication configuration without processing its source."""
    document.load_from_yaml(folder, refresh_header)
    return PublicationWorkflowResult(title=document.title)


def run_publication_command(
    document: PublicationDocument,
    folder: Path,
    command: str,
) -> PublicationWorkflowResult:
    """Load configuration and run one configured command."""
    document.load_from_yaml(folder)
    document.run_command(command)
    return PublicationWorkflowResult(title=document.title)


def process_publication(
    document: PublicationDocument,
    folder: Path,
    *,
    refresh_header: bool = True,
    preprocess: bool = True,
) -> PublicationWorkflowResult:
    """Run the complete authored-source-to-intermediate publication workflow."""
    if preprocess:
        run_publication_command(document, folder, "preprocess")
    document.load_from_yaml(folder, refresh_header)
    document.import_assets(folder / "assets", refresh_header)
    document.load_from_file()
    document.process()
    return PublicationWorkflowResult(title=document.title)
