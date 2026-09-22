"""Tests for framework-neutral publication workflow orchestration."""

from __future__ import annotations

from pathlib import Path

from stringprint2.services.publication_workflow import (
    load_publication,
    process_publication,
    run_publication_command,
)


class FakePublication:
    """Record lifecycle calls without requiring Django."""

    title = "Test publication"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def load_from_yaml(
        self,
        storage_dir: Path,
        refresh_header: bool = False,
    ) -> None:
        self.calls.append(f"load:{refresh_header}")

    def import_assets(self, asset_folder: Path, refresh: bool) -> None:
        self.calls.append(f"assets:{asset_folder.name}:{refresh}")

    def load_from_file(self) -> None:
        self.calls.append("source")

    def process(self) -> None:
        self.calls.append("process")

    def run_command(self, command: str) -> None:
        self.calls.append(f"command:{command}")


def test_process_publication_runs_the_complete_pipeline(tmp_path) -> None:
    """Preprocessing happens before configuration, assets, source, and compilation."""
    document = FakePublication()

    result = process_publication(document, tmp_path)

    assert document.calls == [
        "load:False",
        "command:preprocess",
        "load:True",
        "assets:assets:True",
        "source",
        "process",
    ]
    assert result.title == "Test publication"


def test_process_can_skip_preprocessing_and_refresh(tmp_path) -> None:
    """CLI flags map to explicit workflow options."""
    document = FakePublication()

    process_publication(
        document,
        tmp_path,
        refresh_header=False,
        preprocess=False,
    )

    assert document.calls == [
        "load:False",
        "assets:assets:False",
        "source",
        "process",
    ]


def test_load_and_custom_commands_are_independent_workflows(tmp_path) -> None:
    """Thin delivery commands can invoke configuration or custom actions directly."""
    document = FakePublication()

    load_publication(document, tmp_path, refresh_header=True)
    run_publication_command(document, tmp_path, "publish")

    assert document.calls == [
        "load:True",
        "load:False",
        "command:publish",
    ]
