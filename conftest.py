"""
Root conftest.

The session document-source directory is built in proj/test_settings.py, which
runs early enough to influence settings import. This file only tears it down.
"""

from __future__ import annotations

import stringprint_test_env


def pytest_unconfigure(config) -> None:
    stringprint_test_env.cleanup()
