
import os
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# load settings from config file
with open(os.path.join(BASE_DIR, 'proj', 'conf', 'config.yaml')) as fi:
    config = yaml.load(fi, Loader=yaml.FullLoader)

# if running as a vagrant, need to address through file system
is_vagrant = os.path.exists("/etc/is_vagrant_vm")
if is_vagrant:
    for k, v in config["ORGS"].items():
        v["storage_dir"] = "/sp_" + k + "_storage"
        v["publish_dir"] = "/sp_" + k + "_publish"

# import config settings into module
for k, v in config.items():
    vars()[k] = v

local = "http://127.0.0.1:8001"

LOGIN_REDIRECT_URL = "/"

LIVE_TEST = False

DEBUG = True
IS_LIVE = False
SITE_ROOT = local
PAYPAL_TEST = True

ALLOWED_HOSTS = ["127.0.0.1", "192.168.0.112"]

PROJECT_PATH = os.path.dirname(os.path.realpath(os.path.dirname(__file__)))
MEDIA_ROOT = PROJECT_PATH + '/media/'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',

        'DIRS': [
            PROJECT_PATH + '/templates/',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': DEBUG,
            'context_processors': [
                'proj.universal.universal_context',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


STATIC_DIR = PROJECT_PATH + '/static/'
COMPRESS_ROOT = STATIC_DIR

STATICFILES_DIRS = []

for k, v in config["ORGS"].items():
    static_path = os.path.join(v["storage_dir"], "static")
    if os.path.exists(static_path):
        STATICFILES_DIRS.append(static_path)

STATICFILES_DIRS.append(STATIC_DIR)
COMPRESS_ENABLED = True
# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'compressor',
    'stringprint',
    'bootstrapform',
    'import_export',
    'frontend',
)

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'htmlmin.middleware.MarkRequestMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'htmlmin.middleware.HtmlMinifyMiddleware',
)

ROOT_URLCONF = 'proj.urls'

WSGI_APPLICATION = 'proj.wsgi.application'

# CELERY_RESULT_BACKEND='djcelery.backends.database:DatabaseBackend'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_SEND_TASK_ERROR_EMAILS = True

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

if DEBUG:

    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }

else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': "stringprint1",
        }
    }

if IS_LIVE:
    DATABASES = LIVE_DATEBASES
else:
    if LIVE_TEST:
        print("Connecting to LIVE Data")
        DATABASES = LIVE_DATEBASES_REMOTE
    else:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
            }
        }

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'
MEDIA_URL = "/media/"

SESSION_COOKIE_AGE = 604800
DEBUG = True


STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',

]

COMPRESS_CSS_FILTERS = ["compressor.filters.css_default.CssRelativeFilter",
                        #'compressor.filters.css_default.CssAbsoluteFilter',
                        'compressor.filters.cssmin.rCSSMinFilter']


# not really required - used to configure what is now the back end
SHARE_IMAGE = ""
TWITTER_SHARE_IMAGE = ""
SITE_DESCRIPTION = ""
SITE_TWITTER = ""
GA_CODE = ""
TINYIFY = True
