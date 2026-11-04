"""Explicit startup shared by console and Django management entry points."""

from __future__ import annotations

import os
from pathlib import Path


def configure_environment() -> None:
    """Select settings without overriding caller configuration or changing sys.path."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stringprint2.proj.settings")
    if "STRINGPRINT_CONFIG" in os.environ:
        os.environ["STRINGPRINT_CONFIG"] = str(
            Path(os.environ["STRINGPRINT_CONFIG"]).expanduser().resolve()
        )


def setup_django() -> None:
    configure_environment()
    import django

    django.setup()


def management_main(arguments: list[str] | None = None) -> None:
    configure_environment()
    from django.core.management import execute_from_command_line

    execute_from_command_line(arguments)
