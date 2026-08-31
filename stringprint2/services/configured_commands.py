"""
Resolve and execute configured publication commands.
"""

from __future__ import annotations

import importlib.util
import subprocess
from contextlib import contextmanager
from contextvars import ContextVar
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Iterator, Protocol

from django.template import Context, Template
from pydantic import BaseModel, ConfigDict

CommandRunner = Callable[[list[str], str], int]
active_command_runner: ContextVar[CommandRunner | None] = ContextVar(
    "active_command_runner",
    default=None,
)


@contextmanager
def command_runner_context(runner: CommandRunner) -> Iterator[None]:
    """Use one command runner for nested publication service calls."""
    token = active_command_runner.set(runner)
    try:
        yield
    finally:
        active_command_runner.reset(token)


def run_subprocess_command(arguments: list[str], working_directory: str) -> int:
    """
    Run an external command through the standard subprocess implementation.
    """

    return subprocess.call(arguments, cwd=working_directory)


class CommandOrganisation(Protocol):
    """
    Organisation values required for configured commands.
    """

    commands: Mapping[str, str]
    storage_dir: str


class CommandPublication(Protocol):
    """
    Publication values required for configured commands.
    """

    commands: Mapping[str, str]
    org: CommandOrganisation
    storage_dir: str


class ConfiguredCommand(BaseModel):
    """
    Describe a resolved shell-style publication command.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    template: str
    working_directory: Path


class CommandExecutionResult(BaseModel):
    """
    Describe the outcome of an external configured command.
    """

    model_config = ConfigDict(frozen=True)

    command: ConfiguredCommand
    arguments: tuple[str, ...]
    return_code: int


def resolve_configured_command(
    publication: CommandPublication,
    name: str,
) -> ConfiguredCommand | None:
    """
    Resolve a command, preferring publication configuration over organisation.
    """

    template = publication.org.commands.get(name)
    working_directory = Path(publication.org.storage_dir)
    publication_template = publication.commands.get(name)
    if publication_template is not None:
        template = publication_template
        working_directory = Path(publication.storage_dir)
    if not template:
        return None
    return ConfiguredCommand(
        name=name,
        template=template,
        working_directory=working_directory,
    )


def run_module_command(
    publication: CommandPublication,
    command: ConfiguredCommand,
) -> object:
    """
    Import and invoke a configured module symbol.
    """

    module_path, separator, item_name = command.template.removeprefix(
        "module::"
    ).partition(":")
    if not separator or not item_name:
        raise ValueError(f"Invalid module command: {command.template}")
    if module_path.startswith("$doc/"):
        file_path = Path(publication.storage_dir) / module_path.removeprefix("$doc/")
    elif module_path.startswith("$org/"):
        file_path = Path(publication.org.storage_dir) / module_path.removeprefix(
            "$org/"
        )
    else:
        raise ValueError("Module commands must start with $doc/ or $org/")

    spec = importlib.util.spec_from_file_location(
        "stringprint_configured_module", file_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load configured module: {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    configured_item = getattr(module, item_name)
    result = configured_item(publication)
    if callable(result):
        return result()
    return result


def run_configured_command(
    publication: CommandPublication,
    name: str,
    template_values: Mapping[str, object],
    *,
    runner: CommandRunner | None = None,
) -> CommandExecutionResult | object | None:
    """
    Resolve and run one configured publication command.
    """

    command = resolve_configured_command(publication, name)
    if command is None:
        return None
    if command.template.startswith("module::"):
        return run_module_command(publication, command)

    resolved_runner = runner or active_command_runner.get() or run_subprocess_command
    rendered = Template(command.template).render(
        Context({"article": dict(template_values)})
    )
    arguments = rendered.split(" ")
    return_code = resolved_runner(arguments, str(command.working_directory))
    return CommandExecutionResult(
        command=command,
        arguments=tuple(arguments),
        return_code=return_code,
    )
