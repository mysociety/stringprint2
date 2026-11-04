"""
Settings for the pytest suite.

The fixture bootstrap selects a temporary source repository before production
settings are imported. This module then applies test-only output overrides.
"""

import os
import stringprint_test_env

# must run before proj.settings is imported - see that module's docstring
stringprint_test_env.bootstrap()

from .settings import *  # noqa: E402,F401,F403

DEBUG = False

# Isolate generated static output from both the real repository and authored assets.
STATIC_ROOT = str(stringprint_test_env.STATIC_ROOT) + os.sep
COMPRESS_ROOT = STATIC_ROOT
COMPRESS_URL = STATIC_URL  # noqa: F405
KINDLEGEN_LOC = ""

# settings.py captures DEBUG by value when it builds TEMPLATES, before its own
# later DEBUG = True reassignment, so this has to be set explicitly.
TEMPLATES[0]["OPTIONS"]["debug"] = False  # noqa: F405

# Between them these mean the default test run needs neither sass nor npx:
# static_precompiler short-circuits compile() to a path computation, and
# compressor passes the block through. The bake tests re-enable both, because
# Article.render reads compressed_files, which only the post_compress signal
# populates.
COMPRESS_ENABLED = False
STATIC_PRECOMPILER_DISABLE_AUTO_COMPILE = True

# no TinyPNG API calls - create_tiny falls back to a plain PIL save
TINYIFY = False

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
