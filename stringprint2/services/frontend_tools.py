"""Resolve the engine's locked frontend toolchain independently of cwd."""

from __future__ import annotations

import os
import json
from pathlib import Path


def node_modules() -> Path:
    override = os.environ.get("STRINGPRINT_NODE_MODULES")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / "node_modules"


def frontend_tool(name: str) -> str:
    return str(node_modules() / ".bin" / name)


def frontend_package(name: str) -> str:
    package = node_modules() / name
    manifest = json.loads((package / "package.json").read_text())
    return str(package / manifest.get("main", "index.js"))
