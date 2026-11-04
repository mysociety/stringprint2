"""
Point the app at a throwaway copy of the fixture document source.

proj/settings.py reads its config file when it is imported, and derives
STATICFILES_DIRS, ORG_TEMPLATE_DIRS and TEMPLATES[0]["DIRS"] from
ORGS[<slug>]["storage_dir"] there and then. So STRINGPRINT_CONFIG has to be set
before that import - which is why bootstrap() is called from the top of
proj/test_settings.py rather than from a conftest. pytest-django runs
django.setup() inside pytest_load_initial_conftests, ahead of conftest import,
so a conftest would be too late.

The tree is copied rather than used in place because the app writes into it:
Version.process -> update_paragraph_links -> save_paragraph_links rewrites
_paragraphs.yaml inside the document folder, and import_assets writes derived
images into MEDIA_ROOT.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import yaml

FIXTURES = Path(__file__).parent / "tests" / "fixtures"
REAL_STATIC_ROOT = Path(__file__).parent / "stringprint2" / "static_sources"

SESSION_ROOT: Optional[Path] = None
DOC_SOURCE: Optional[Path] = None
MEDIA_ROOT: Optional[Path] = None
STATIC_ROOT: Optional[Path] = None
CONFIG_FILE: Optional[Path] = None


def bootstrap() -> Path:
    """
    Build the session directory and set STRINGPRINT_CONFIG. Idempotent.
    """
    global SESSION_ROOT, DOC_SOURCE, MEDIA_ROOT, STATIC_ROOT, CONFIG_FILE

    if SESSION_ROOT is not None:
        return CONFIG_FILE

    SESSION_ROOT = Path(tempfile.mkdtemp(prefix="stringprint-tests-"))
    DOC_SOURCE = SESSION_ROOT / "doc_source"
    MEDIA_ROOT = SESSION_ROOT / "media"
    # Build products are isolated; authored static assets stay read-only.
    STATIC_ROOT = SESSION_ROOT / "static"

    shutil.copytree(str(FIXTURES / "doc_source"), str(DOC_SOURCE))
    MEDIA_ROOT.mkdir()
    STATIC_ROOT.mkdir()

    config = {
        "CHROME_DRIVER": "/usr/bin/chromedriver",
        "KINDLEGEN_LOC": "/nonexistent/kindlegen",
        "SITE_NAME": "stringprint-test",
        "SECRET_KEY": "test-only-not-a-secret",
        # empty key keeps create_tiny on its offline PIL branch
        "TINY_PNG_KEY": "",
        # trailing separator matters - see proj/settings.py
        "MEDIA_ROOT": str(MEDIA_ROOT) + os.sep,
        "ORGS": {"default": {"storage_dir": str(DOC_SOURCE)}},
    }

    CONFIG_FILE = SESSION_ROOT / "config.yaml"
    with open(str(CONFIG_FILE), "w") as file_handle:
        yaml.safe_dump(config, file_handle)

    os.environ["STRINGPRINT_CONFIG"] = str(CONFIG_FILE)
    return CONFIG_FILE


def cleanup() -> None:
    if SESSION_ROOT is not None:
        shutil.rmtree(str(SESSION_ROOT), ignore_errors=True)
