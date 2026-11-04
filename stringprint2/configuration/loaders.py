"""
Load and validate Stringprint YAML configuration files.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ValidationError
from ruamel.yaml import YAML

from .models import (
    AssetCollection,
    OrganisationConfig,
    PublicationConfig,
    RepositoryConfig,
)


class ConfigurationError(ValueError):
    """
    Report configuration validation failures with their source path.
    """

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Invalid configuration in {path}:\n{reason}")


def load_yaml(path: Path) -> object:
    """
    Read one YAML document without constructing arbitrary Python objects.
    """
    try:
        with path.open(encoding="utf-8") as file_handle:
            return YAML(typ="safe").load(file_handle)
    except OSError as error:
        raise ConfigurationError(path, str(error)) from error
    except Exception as error:
        raise ConfigurationError(path, f"invalid YAML: {error}") from error


def validate_config[Configuration: BaseModel](
    path: Path, model: type[Configuration]
) -> Configuration:
    """
    Validate one YAML document against the supplied configuration model.
    """
    try:
        return model.model_validate(load_yaml(path))
    except ValidationError as error:
        raise ConfigurationError(path, str(error)) from error


def load_repository_config(path: Path) -> RepositoryConfig:
    """
    Load the application-level repository configuration.
    """
    return validate_config(path, RepositoryConfig)


def load_organisation_config(path: Path) -> OrganisationConfig:
    """
    Load organisation-wide publication configuration.
    """
    return validate_config(path, OrganisationConfig)


def load_publication_config(path: Path) -> PublicationConfig:
    """Validate authored publication values; the load plan resolves org defaults."""
    return validate_config(path, PublicationConfig)


def load_assets_config(path: Path) -> AssetCollection:
    """
    Load a publication's ordered asset definitions.
    """
    return validate_config(path, AssetCollection)
