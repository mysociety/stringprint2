"""Typed parsing for Stringprint's command-shell invocation syntax."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict


class ShellOptions(BaseModel):
    """Flags and command groups passed to the interactive command shell."""

    model_config = ConfigDict(frozen=True)

    start_server: bool = True
    continue_in_shell: bool = False
    refresh: bool = False
    commands: tuple[tuple[str, ...], ...] = ()


def parse_shell_options(arguments: Sequence[str]) -> ShellOptions:
    """Parse global flags and command argument groups."""
    start_server = True
    continue_in_shell = False
    refresh = False
    command_tokens: list[str] = []

    for argument in arguments:
        if argument == "--no-server":
            start_server = False
        elif argument == "--continue":
            continue_in_shell = True
        elif argument == "--refresh":
            refresh = True
        else:
            command_tokens.append(argument)

    if command_tokens in (["?"], ["help"]):
        command_tokens = ["--help"]

    commands: list[tuple[str, ...]] = []
    current: list[str] = []
    for token in command_tokens:
        if token.startswith("--") and token not in {
            "--no-preprocess",
            "--no-refresh",
            "--no-hero",
            "--no-thumbnail",
            "--no-render-zip",
        }:
            if current:
                commands.append(tuple(current))
            current = [token.removeprefix("--")]
        else:
            current.append(token)
    if current:
        commands.append(tuple(current))

    return ShellOptions(
        start_server=start_server,
        continue_in_shell=continue_in_shell,
        refresh=refresh,
        commands=tuple(commands),
    )
