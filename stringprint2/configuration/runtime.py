"""Validated application configuration, independent of Django initialization."""

from __future__ import annotations

import os
from pathlib import Path
from shutil import copyfile

from .loaders import load_repository_config
from .models import RepositoryConfig


def runtime_config_path() -> Path:
    """Honor an explicit config, retaining the historical local default."""
    override = os.environ.get("STRINGPRINT_CONFIG")
    if override:
        path = Path(override).expanduser().resolve()
        if not path.is_file():
            raise RuntimeError(f"STRINGPRINT_CONFIG points at a missing file: {path}")
        return path
    folder = Path(__file__).resolve().parents[1] / "proj" / "conf"
    path = folder / "config.yaml"
    if not path.exists() and (folder / "config-example.yaml").exists():
        copyfile(folder / "config-example.yaml", path)
    return path


def load_runtime_config(path: Path) -> RepositoryConfig:
    """Resolve authored paths relative to the configuration file, never cwd."""
    config = load_repository_config(path)

    def absolute(value: Path | None) -> Path | None:
        if value is None:
            return None
        value = value.expanduser()
        return (
            value.resolve() if value.is_absolute() else (path.parent / value).resolve()
        )

    organisations = {}
    for slug, organisation in config.organisations.items():
        storage = absolute(organisation.storage_dir)
        publish = absolute(organisation.publish_dir)
        if Path("/etc/is_vagrant_vm").exists():
            storage = Path(f"/sp_{slug}_storage")
            if publish is not None:
                publish = Path(f"/sp_{slug}_publish")
        organisations[slug] = organisation.model_copy(
            update={
                "storage_dir": storage,
                "publish_dir": publish,
            }
        )
    return config.model_copy(
        update={
            "organisations": organisations,
            "media_root": absolute(config.media_root),
            "chrome_driver": absolute(config.chrome_driver),
            "kindlegen_location": absolute(config.kindlegen_location),
        }
    )
