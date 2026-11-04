from pathlib import Path
from types import SimpleNamespace
import os
import subprocess
import sys
import pytest
from stringprint2.configuration.loaders import ConfigurationError
from stringprint2.configuration.runtime import load_runtime_config

def test_entry_point_import_does_not_initialize_django(tmp_path):
    environment = {**os.environ, "DJANGO_SETTINGS_MODULE": "caller.settings"}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os, sys; import stringprint2.__main__; "
            "assert os.environ['DJANGO_SETTINGS_MODULE'] == 'caller.settings'; "
            "assert 'django' not in sys.modules",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_runtime_paths_do_not_depend_on_working_directory(tmp_path, monkeypatch):
    config = tmp_path / "config.yaml"
    config.write_text(
        "SITE_NAME: test\nSECRET_KEY: test\nORGS:\n  test:\n    storage_dir: sources\n    publish_dir: output\n"
    )
    monkeypatch.chdir(tmp_path.parent)
    loaded = load_runtime_config(config)
    assert loaded.organisations["test"].storage_dir == tmp_path / "sources"
    assert loaded.organisations["test"].publish_dir == tmp_path / "output"
    config.write_text(config.read_text() + "UNSUPPORTED: true\n")
    with pytest.raises(ConfigurationError, match="UNSUPPORTED"):
        load_runtime_config(config)


def test_legacy_imports_are_aliases_of_the_canonical_models():
    import stringprint.models
    import stringprint2.stringprint.models
    from django.apps import apps

    assert stringprint.models is stringprint2.stringprint.models
    assert (
        apps.get_model("stringprint", "Article")
        is stringprint2.stringprint.models.Article
    )


def test_empty_publish_path_retains_default_output_location(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(
        'SITE_NAME: test\nSECRET_KEY: test\nORGS:\n  test:\n    storage_dir: sources\n    publish_dir: ""\n'
    )
    assert load_runtime_config(config).organisations["test"].publish_dir is None

