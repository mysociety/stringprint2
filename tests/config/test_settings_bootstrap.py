"""
The settings bootstrap is what lets the suite point the app at a fixture
document source. It is deliberately independent of every other fixture, so
that `pytest tests/config/test_settings_bootstrap.py` stays usable as a
first-response diagnostic when a Django upgrade breaks settings import.
"""

from __future__ import annotations

import os
from django.conf import settings
from django.template.loader import get_template

from stringprint_test_env import CONFIG_FILE, DOC_SOURCE, MEDIA_ROOT, STATIC_ROOT


def test_config_override_is_in_use() -> None:
    assert os.environ["STRINGPRINT_CONFIG"].endswith("config.yaml")
    assert settings.ORGS["default"]["storage_dir"] == str(DOC_SOURCE)


def test_the_override_branch_was_taken() -> None:
    """
    settings.py only seeds config.yaml from config-example.yaml on the default
    branch, so proving the override branch ran is what proves the repo's own
    config was left alone. Asserting the in-tree config is absent would not
    work - it is gitignored and legitimately present after any normal run.
    """
    import proj.settings

    assert proj.settings.config_file == CONFIG_FILE
    assert proj.settings.config_override == str(CONFIG_FILE)


def test_media_root_points_at_the_session_directory() -> None:
    assert settings.MEDIA_ROOT == str(MEDIA_ROOT) + os.sep
    # create_responsive and create_tiny concatenate onto this
    assert settings.MEDIA_ROOT.endswith(os.sep)


def test_static_root_points_at_the_session_directory() -> None:
    """
    Regression test: STATIC_ROOT/COMPRESS_ROOT used to default to the real
    stringprint2/static/ dir even under pytest (only MEDIA_ROOT was
    session-scoped), so the bake/scss tests wrote compiled CSS there -
    gitignored, so invisible to git, but a real dev server run afterwards in
    the same working tree would serve that stale output (test fixtures use
    org slug "default" too) instead of recompiling, with no error to say so.
    """
    assert settings.STATIC_ROOT == str(STATIC_ROOT) + os.sep
    # COMPRESS_ROOT is AppConf-derived (compressor/conf.py's configure_root),
    # which runs os.path.abspath() on it - normalised, so no trailing sep
    assert os.path.normcase(os.path.abspath(settings.COMPRESS_ROOT)) == (
        os.path.normcase(os.path.abspath(settings.STATIC_ROOT))
    )


def test_authored_assets_are_separate_from_build_outputs() -> None:
    from django.contrib.staticfiles import finders
    from stringprint_test_env import REAL_STATIC_ROOT
    assert finders.find("css/fa_reduced.css") == str(REAL_STATIC_ROOT / "css" / "fa_reduced.css")
    assert not (STATIC_ROOT / "css" / "fa_reduced.css").exists()


def test_org_static_dir_is_derived_from_storage_dir() -> None:
    assert ("orgs/default", str(DOC_SOURCE / "_static")) in settings.STATICFILES_DIRS


def test_org_template_dir_is_derived_from_storage_dir() -> None:
    assert ("default/templates", str(DOC_SOURCE / "_templates")) in (
        settings.ORG_TEMPLATE_DIRS
    )
    assert settings.ORG_TEMPLATE_DIRS[0] in (
        settings.TEMPLATES[0]["OPTIONS"]["loaders"][0][1]
    )


def test_namespace_aware_loader_resolves_the_org_template() -> None:
    template = get_template("default/templates/ink//article_main.html")
    assert "ORG_TEMPLATE_OVERRIDE_MARKER" in template.template.source


def test_autoreload_can_enumerate_template_directories() -> None:
    """
    Regression test for a script/server crash: NamespaceAwareLoader is
    configured with ORG_TEMPLATE_DIRS as its own `dirs` (see settings.py's
    TEMPLATES), which holds (namespace, path) tuples - fine for
    get_template_sources()/namespace_aware_dirs(), which know to unpack
    them, but django.template.autoreload.get_template_directories() (used
    by the dev server's autoreload watcher) calls every loader's
    get_dirs() expecting plain paths, and TypeErrors on a tuple.
    """
    from django.template.autoreload import get_template_directories

    directories = list(get_template_directories())
    assert directories
    assert all(not isinstance(d, tuple) for d in directories)


def test_test_only_overrides_are_applied() -> None:
    assert settings.DEBUG is False
    assert settings.TEMPLATES[0]["OPTIONS"]["debug"] is False
    assert settings.COMPRESS_ENABLED is False
    assert settings.STATIC_PRECOMPILER_DISABLE_AUTO_COMPILE is True
