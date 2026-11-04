from pathlib import Path
from types import SimpleNamespace
import os
import subprocess
import sys
import pytest
from stringprint2.configuration.loaders import ConfigurationError
from stringprint2.configuration.runtime import load_runtime_config
from stringprint2.services.document_compilation import compile_document

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


def test_compilation_needs_no_database_and_reports_missing_assets():
    compiled = compile_document(
        "# Title\n\n[asset:photo]\n\n[asset:missing]", seed=13, assets={"photo": 17}
    )
    assert compiled.used_asset_ids == frozenset({17})
    assert compiled.diagnostics == ("Asset missing: missing",)
    assert compiled.sections[0].grafs[0].asset == 17


def test_legacy_imports_are_aliases_of_the_canonical_models():
    import stringprint.models
    import stringprint2.stringprint.models
    from django.apps import apps

    assert stringprint.models is stringprint2.stringprint.models
    assert (
        apps.get_model("stringprint", "Article")
        is stringprint2.stringprint.models.Article
    )


def test_browser_is_closed_when_capture_fails(monkeypatch):
    from stringprint2.services.paragraph_screenshots import paragraph_browser

    closed = []
    browser = SimpleNamespace(
        new_page=lambda: object(), close=lambda: closed.append("browser")
    )

    class Playwright:
        chromium = SimpleNamespace(launch=lambda: browser)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            closed.append("playwright")

    monkeypatch.setattr(
        "stringprint2.services.paragraph_screenshots.sync_playwright", Playwright
    )
    with pytest.raises(RuntimeError, match="capture failed"):
        with paragraph_browser():
            raise RuntimeError("capture failed")
    assert closed == ["browser", "playwright"]


def test_compilation_preserves_process_random_state():
    import random

    state = random.getstate()
    compile_document("# Test\n\nA paragraph.", seed=13, assets={})
    assert random.getstate() == state


def test_empty_publish_path_retains_default_output_location(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(
        'SITE_NAME: test\nSECRET_KEY: test\nORGS:\n  test:\n    storage_dir: sources\n    publish_dir: ""\n'
    )
    assert load_runtime_config(config).organisations["test"].publish_dir is None

