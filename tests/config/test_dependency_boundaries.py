"""Dependency-boundary checks for retired vendored framework code."""

from __future__ import annotations

import ast
from pathlib import Path


def test_application_code_does_not_import_useful_inkleby() -> None:
    """Application code and historical migrations use project-owned imports."""
    package_root = Path(__file__).parents[2] / "stringprint2"
    violations: list[str] = []

    for source_path in package_root.rglob("*.py"):
        relative_path = source_path.relative_to(package_root)
        tree = ast.parse(
            source_path.read_text(encoding="utf-8"), filename=str(source_path)
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            if any(
                module == "useful_inkleby" or module.startswith("useful_inkleby.")
                for module in modules
            ):
                violations.append(f"{relative_path}:{node.lineno}")

    assert violations == []
