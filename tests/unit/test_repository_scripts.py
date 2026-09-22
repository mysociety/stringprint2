"""Tests for repository-level development scripts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SHELL_SCRIPTS = ("bootstrap", "setup", "update", "console", "server")


@pytest.fixture
def command_environment(tmp_path: Path) -> tuple[dict[str, str], Path]:
    """Provide harmless git and Poetry commands that record their arguments."""
    command_directory = tmp_path / "bin"
    command_directory.mkdir()
    command_log = tmp_path / "commands.log"
    for command in ("git", "poetry"):
        executable = command_directory / command
        executable.write_text(
            f'#!/bin/sh\nprintf "{command} %s\\n" "$*" >> "$SCRIPT_COMMAND_LOG"\n'
        )
        executable.chmod(0o755)
    environment = os.environ.copy()
    environment["PATH"] = f"{command_directory}{os.pathsep}{environment['PATH']}"
    environment["SCRIPT_COMMAND_LOG"] = str(command_log)
    return environment, command_log


def run_script(
    script_name: str,
    environment: dict[str, str],
    working_directory: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    """Run a repository script from an unrelated working directory."""
    return subprocess.run(
        (str(REPOSITORY_ROOT / "script" / script_name), *arguments),
        cwd=working_directory,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def test_shell_scripts_are_root_aware_and_fail_fast() -> None:
    """Every launcher can be called outside the repository without hidden cwd state."""
    for script_name in SHELL_SCRIPTS:
        script = REPOSITORY_ROOT / "script" / script_name
        source = script.read_text()

        assert os.access(script, os.X_OK)
        assert source.startswith("#!/bin/sh\n")
        assert "set -eu" in source
        assert 'cd "$REPOSITORY_ROOT"' in source


def test_update_initializes_dependencies_and_applies_migrations(
    tmp_path: Path,
    command_environment: tuple[dict[str, str], Path],
) -> None:
    """Updating reaches the current manage.py through Poetry with no prompts."""
    environment, command_log = command_environment

    run_script("update", environment, tmp_path)

    assert command_log.read_text().splitlines() == [
        "git submodule update --init --recursive",
        "poetry install --no-interaction --no-root",
        (
            "poetry run python stringprint2/stringprint2/manage.py "
            "makemigrations --check --dry-run"
        ),
        ("poetry run python stringprint2/stringprint2/manage.py migrate --noinput"),
    ]


def test_server_forwards_arguments_through_poetry(
    tmp_path: Path,
    command_environment: tuple[dict[str, str], Path],
) -> None:
    """The development server launcher uses the project environment and forwards flags."""
    environment, command_log = command_environment

    run_script("server", environment, tmp_path, "--noreload")

    assert command_log.read_text().strip() == (
        "poetry run python stringprint2/stringprint2/manage.py "
        "runserver 0.0.0.0:8000 --noreload"
    )


def test_setup_delegates_database_work_to_update() -> None:
    """Setup has one migration path rather than retaining a stale manage wrapper."""
    source = (REPOSITORY_ROOT / "script" / "setup").read_text()

    assert "exec script/update" in source
    assert "stringprint2/stringprint2/script/manage" not in source


def test_console_uses_the_package_module_entry_point() -> None:
    """The console uses the package module without depending on an internal file path."""
    source = (REPOSITORY_ROOT / "script" / "console").read_text()

    assert 'exec poetry run python -m stringprint2 "$@"' in source


def test_console_module_imports_with_legacy_django_apps_available() -> None:
    """Package execution bootstraps the legacy top-level Django app names early."""
    subprocess.run(
        (sys.executable, "-c", "import stringprint2.__main__"),
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
