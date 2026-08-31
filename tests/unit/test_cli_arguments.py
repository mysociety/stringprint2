"""Tests for typed command-shell argument parsing."""

from __future__ import annotations

from stringprint2.cli_arguments import parse_shell_options


def test_global_flags_are_not_forwarded_as_commands() -> None:
    """Lifecycle flags configure the shell independently from commands."""
    options = parse_shell_options(
        ["--no-server", "--refresh", "--process", "minimal-doc", "--render"]
    )

    assert options.start_server is False
    assert options.refresh is True
    assert options.commands == (("process", "minimal-doc"), ("render",))


def test_continue_keeps_the_interactive_shell_open() -> None:
    """The continue flag is retained without creating an empty command."""
    options = parse_shell_options(["--continue", "--listdocs"])

    assert options.continue_in_shell is True
    assert options.commands == (("listdocs",),)


def test_help_aliases_map_to_the_shell_help_command() -> None:
    """Question-mark and plain help use cmd.Cmd's help command."""
    assert parse_shell_options(["?"]).commands == (("help",),)
    assert parse_shell_options(["help"]).commands == (("help",),)


def test_no_arguments_produce_no_commands() -> None:
    """An empty invocation enters the interactive shell directly."""
    assert parse_shell_options([]).commands == ()
