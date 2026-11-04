"""Standalone engine launcher contracts."""
from pathlib import Path
import os
import subprocess
import pytest

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


def test_engine_manage_launcher_resolves_the_current_layout(
    tmp_path: Path, command_environment: tuple[dict[str, str], Path]
) -> None:
    """
    The standalone engine launcher finds manage.py from an unrelated directory.
    """
    environment, command_log = command_environment
    engine = Path(__file__).resolve().parents[2]
    subprocess.run(
        [str(engine / "script" / "manage"), "check"],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert (
        command_log.read_text().strip()
        == f"poetry run python {engine}/stringprint2/manage.py check"
    )
