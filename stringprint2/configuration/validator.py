"""
Validate a complete Stringprint document-source repository.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .loaders import (
    ConfigurationError,
    load_assets_config,
    load_organisation_config,
    load_publication_config,
)


class ValidationIssue(BaseModel):
    """
    Describe one invalid configuration file.
    """

    model_config = ConfigDict(frozen=True)

    path: Path
    message: str


class ValidationReport(BaseModel):
    """
    Summarise a complete document-source validation run.
    """

    model_config = ConfigDict(frozen=True)

    source: Path
    publication_count: int = 0
    asset_manifest_count: int = 0
    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """
        Return whether every discovered configuration file was valid.
        """
        return not self.issues


def issue_from_error(error: ConfigurationError) -> ValidationIssue:
    """
    Convert a loader exception into a serialisable validation issue.
    """
    return ValidationIssue(path=error.path, message=error.reason)


def validate_document_source(source: Path) -> ValidationReport:
    """
    Validate organisation, publication, and asset configuration files.

    Every discoverable file is checked so one run reports all failures. The
    function only reads the source repository.
    """
    source = source.resolve()
    issues: list[ValidationIssue] = []
    organisation_path = source / "_conf" / "settings.yaml"

    try:
        organisation = load_organisation_config(organisation_path)
    except ConfigurationError as error:
        return ValidationReport(source=source, issues=[issue_from_error(error)])

    publication_count = 0
    asset_manifest_count = 0
    for document_path in sorted((source / "_docs").glob("*/settings.yaml")):
        try:
            load_publication_config(document_path, organisation)
            publication_count += 1
        except ConfigurationError as error:
            issues.append(issue_from_error(error))

        assets_path = document_path.parent / "assets" / "assets.yaml"
        if not assets_path.exists():
            continue
        try:
            load_assets_config(assets_path)
            asset_manifest_count += 1
        except ConfigurationError as error:
            issues.append(issue_from_error(error))

    return ValidationReport(
        source=source,
        publication_count=publication_count,
        asset_manifest_count=asset_manifest_count,
        issues=issues,
    )
