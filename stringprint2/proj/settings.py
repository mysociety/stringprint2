import os
from pathlib import Path

from stringprint2.configuration.runtime import load_runtime_config, runtime_config_path

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
config_override = os.environ.get("STRINGPRINT_CONFIG")
config_file = runtime_config_path()
runtime_config = load_runtime_config(config_file)

SECRET_KEY = runtime_config.secret_key
SITE_NAME = runtime_config.site_name
TINY_PNG_KEY = runtime_config.tiny_png_key
CHROME_DRIVER = str(runtime_config.chrome_driver or "")
KINDLEGEN_LOC = str(runtime_config.kindlegen_location or "")
ORGS = {
    slug: {
        "storage_dir": str(organisation.storage_dir),
        **(
            {"publish_dir": str(organisation.publish_dir)}
            if organisation.publish_dir
            else {}
        ),
    }
    for slug, organisation in runtime_config.organisations.items()
}

local = "http://127.0.0.1:8000"

LOGIN_REDIRECT_URL = "/"

LIVE_TEST = False

DEBUG = True
IS_LIVE = False
SITE_ROOT = local
PAYPAL_TEST = True

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

PROJECT_PATH = os.path.dirname(os.path.realpath(os.path.dirname(__file__)))
# Keep existing local installations usable; new installs keep writable state
# alongside their document repository rather than inside site-packages.
STATE_ROOT = Path(
    os.environ.get(
        "STRINGPRINT_STATE_DIR",
        str(
            next(iter(runtime_config.organisations.values())).storage_dir
            / ".stringprint"
        ),
    )
)
STATE_ROOT.mkdir(parents=True, exist_ok=True)
legacy_media = Path(PROJECT_PATH) / "media"
MEDIA_ROOT = (
    str(
        runtime_config.media_root
        or (legacy_media if legacy_media.exists() else STATE_ROOT / "media")
    )
    + os.sep
)
STATIC_ROOT = PROJECT_PATH + "/static/"
COMPRESS_ROOT = STATIC_ROOT

STATICFILES_DIRS = [
    (PROJECT_PATH + "/web/"),
    ("vendor", PROJECT_PATH + "/vendor/"),
]

ORG_TEMPLATE_DIRS = []

for k, v in ORGS.items():
    static_path = os.path.join(v["storage_dir"], "_static")
    if os.path.exists(static_path):
        STATICFILES_DIRS.append(("orgs/" + k, static_path))

for k, v in ORGS.items():
    static_path = os.path.join(v["storage_dir"], "_templates")
    if os.path.exists(static_path):
        ORG_TEMPLATE_DIRS.append((k + "/templates", static_path))

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [PROJECT_PATH + "/templates/"],
        "OPTIONS": {
            "debug": DEBUG,
            "loaders": [
                (
                    "stringprint2.proj.loaders.NamespaceAwareLoader",
                    ORG_TEMPLATE_DIRS + [PROJECT_PATH + "/templates/"],
                ),
                "django.template.loaders.app_directories.Loader",
            ],
            "context_processors": [
                "stringprint2.proj.universal.universal_context",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.request",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

COMPRESS_ENABLED = True

INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "compressor",
    "stringprint2.stringprint",
    "import_export",
    "stringprint2.frontend",
    "stringprint2.publication_management",
    "static_precompiler",
)

# Retain the primary-key type used by the historical migrations.
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

MIDDLEWARE = (
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "htmlmin.middleware.MarkRequestMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "htmlmin.middleware.HtmlMinifyMiddleware",
)

ROOT_URLCONF = "stringprint2.proj.urls"

WSGI_APPLICATION = "stringprint2.proj.wsgi.application"

# CELERY_RESULT_BACKEND='djcelery.backends.database:DatabaseBackend'
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_SEND_TASK_ERROR_EMAILS = True

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

if DEBUG:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    }

else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "stringprint1",
        }
    }

legacy_database = Path(BASE_DIR) / "db.sqlite3"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(
            legacy_database if legacy_database.is_file() else STATE_ROOT / "db.sqlite3"
        ),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = "/static/"
MEDIA_URL = "/media/"

SESSION_COOKIE_AGE = 604800
DEBUG = True


STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
    "static_precompiler.finders.StaticPrecompilerFinder",
]

COMPRESS_CSS_FILTERS = [
    "compressor.filters.css_default.CssRelativeFilter",
    #'compressor.filters.css_default.CssAbsoluteFilter',
    #'compressor.filters.cssmin.rCSSMinFilter',
    "stringprint2.stringprint.compiler.SVGSafeMinify",
]


bootstrap_sass = os.path.join(PROJECT_PATH, "vendor", "bootstrap", "scss")

normal_scss = os.path.join(PROJECT_PATH, "web", "scss")


STATIC_PRECOMPILER_COMPILERS = (
    (
        "stringprint2.stringprint.compiler.CustomSCSS",
        {
            # ""
            "executable": "/usr/bin/sass",
            "sourcemap_enabled": False,
            "compass_enabled": False,
            "precision": 2,
            "load_paths": [bootstrap_sass, normal_scss],
        },
    ),
)

# not really required - used to configure what is now the back end
SHARE_IMAGE = ""
TWITTER_SHARE_IMAGE = ""
SITE_DESCRIPTION = ""
SITE_TWITTER = ""
GA_CODE = ""
TINYIFY = True
