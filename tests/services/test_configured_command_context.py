"""Tests for scoped configured-command runner injection."""

from __future__ import annotations

from types import SimpleNamespace
import subprocess

import pytest

from stringprint2.services.configured_commands import (
    command_runner_context,
    run_configured_command,
)


def test_context_runner_applies_only_within_managed_execution() -> None:
    """Nested model services use worker supervision without changing their API."""
    publication = SimpleNamespace(
        commands={"publish": "tool --slug {{ article.slug }}"},
        storage_dir="/publication",
        org=SimpleNamespace(commands={}, storage_dir="/organisation"),
    )
    calls = []

    def runner(arguments, working_directory):
        calls.append((arguments, working_directory))
        return 7

    with (
        command_runner_context(runner),
        pytest.raises(subprocess.CalledProcessError) as error,
    ):
        run_configured_command(
            publication,
            "publish",
            {"slug": "example"},
        )

    assert error.value.returncode == 7
    assert calls == [(["tool", "--slug", "example"], "/publication")]
