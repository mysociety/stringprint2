"""
Tests for strict authored-configuration loading.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import stringprint_test_env
from stringprint2.configuration import (
    ConfigurationError,
    load_assets_config,
    load_organisation_config,
    load_publication_config,
    load_repository_config,
)

FIXTURE_SOURCE = stringprint_test_env.FIXTURES / "doc_source"
FIXTURE_DOCUMENTS = FIXTURE_SOURCE / "_docs"


@pytest.fixture
def organisation():
    """
    Return the fixture organisation configuration.
    """
    return load_organisation_config(FIXTURE_SOURCE / "_conf" / "settings.yaml")


@pytest.mark.parametrize(
    "settings_path",
    sorted(FIXTURE_DOCUMENTS.glob("*/settings.yaml")),
    ids=lambda path: path.parent.name,
)
def test_fixture_publications_are_valid(settings_path: Path, organisation) -> None:
    publication = load_publication_config(settings_path, organisation)

    assert publication.title
    assert publication.repo_slug == settings_path.parent.name


@pytest.mark.parametrize(
    "assets_path",
    sorted(FIXTURE_DOCUMENTS.glob("*/assets/assets.yaml")),
    ids=lambda path: path.parent.parent.name,
)
def test_fixture_assets_are_valid(assets_path: Path) -> None:
    assets = load_assets_config(assets_path)

    assert isinstance(assets.root, list)


def test_repository_example_is_valid() -> None:
    config_path = (
        Path(__file__).parents[2]
        / "stringprint2"
        / "proj"
        / "conf"
        / "config-example.yaml"
    )

    config = load_repository_config(config_path)

    assert "default" in config.organisations


def test_unknown_publication_keys_are_rejected(
    tmp_path: Path,
    organisation,
) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        """
        title: Test
        short_title: Test
        description: Test
        byline: Test
        authors: Test
        cite_as: Test
        file_source: document.md
        publish_date: 2026-01-01
        repo_slug: test
        unsupported_setting: true
        """,
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="unsupported_setting"):
        load_publication_config(config_path, organisation)


def test_validation_errors_include_the_source_path(
    tmp_path: Path,
    organisation,
) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text("title: Incomplete\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match=str(config_path)):
        load_publication_config(config_path, organisation)
