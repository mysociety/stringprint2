"""Import-safe console entry point."""
from __future__ import annotations


def main(arguments: list[str] | None = None) -> None:
    from stringprint2.bootstrap import setup_django
    setup_django()
    from stringprint2.cli import main as run_console
    run_console(arguments)


if __name__ == "__main__":
    main()
