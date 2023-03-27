import os
import google.cloud.storage
from django_gcp.storage.bucket_registry import register_gcs_bucket


def get_db_conf():
    """
    Configures database according to the DATABASE_ENGINE environment
    variable. Defaults to SQlite.
    This method is used to let tests run against different database backends.
    """
    database_engine = os.environ.get("DATABASE_ENGINE", "sqlite")
    if database_engine == "sqlite":
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
    elif database_engine == "postgres":
        return {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": "postgres_db",
            "USER": "postgres_user",
            "PASSWORD": "postgres_password",
            "HOST": "localhost",
            "PORT": "5432",
        }


# ---------------------------------------------------------------------------
# GENERIC DJANGO SETTINGS FOR THE TEST APP (scroll down for the good stuff)
# ---------------------------------------------------------------------------

DEBUG = False

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(PROJECT_DIR)

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.admin",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",  # Gives us shell_plus and reset_db for manipulating the test server
    "django_gcp",
    "tests.server.example",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(PROJECT_DIR, "django_gcp", "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

ALLOWED_HOSTS = [
    "localhost",
    ".loca.lt",
]  # Adding loca.lt allows developers to expose the example server using localtunnel

DATABASES = {"default": get_db_conf()}

ROOT_URLCONF = "tests.server.urls"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

SECRET_KEY = "secretkey"

ASGI_APPLICATION = "tests.server.asgi.application"

# ---------------------------------------------------------------------------
# HERE'S HOW TO SET UP ERROR REPORTING AND STRUCTURED LOGGING
# ----------------------------------------------------------------------------

GCP_ERROR_REPORTING_SERVICE_NAME = "django-gcp-example"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "root": {"handlers": ["gcp_structured_logging", "gcp_error_reporting"]},
    "formatters": {
        "verbose": {"format": "%(levelname)s %(asctime)s %(module)s " "%(message)s"},
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "gcp_structured_logging": {
            "level": "INFO",
            "filters": ["require_debug_false"],
            "class": "django_gcp.logging.GoogleStructuredLogsHandler",
        },
        "gcp_error_reporting": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django_gcp.logging.GoogleErrorReportingHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "gcp_structured_logging", "gcp_error_reporting"],
            "level": "INFO",
        },
        "django.server": {
            "handlers": ["console", "gcp_structured_logging", "gcp_error_reporting"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


# ---------------------------------------------------------------------------
# HERE'S HOW TO SET UP STATIC AND MEDIA STORAGE
# ---------------------------------------------------------------------------

# MEDIA FILES
DEFAULT_FILE_STORAGE = "django_gcp.storage.GoogleCloudMediaStorage"
GCP_STORAGE_MEDIA = {"bucket_name": "example-media-assets"}
MEDIA_URL = f"https://storage.googleapis.com/{GCP_STORAGE_MEDIA['bucket_name']}/"
MEDIA_ROOT = "/media/"

# STATIC FILES
STATICFILES_STORAGE = "django_gcp.storage.GoogleCloudStaticStorage"
GCP_STORAGE_STATIC = {"bucket_name": "example-static-assets"}
STATIC_URL = f"https://storage.googleapis.com/{GCP_STORAGE_STATIC['bucket_name']}/"
STATIC_ROOT = "/static/"


# ---------------------------------------------------------------------------
# HERE'S HOW TO SET UP TASKS
# ---------------------------------------------------------------------------

GCP_TASKS_DEFAULT_QUEUE_NAME = "example-primary"
GCP_TASKS_DELIMITER = "--"
# This is the domain on which the worker app can receive requests
# You can use localtunnel to easily create your own public domain to
# run end-to-end integration tests with a real GCP project
GCP_TASKS_DOMAIN = "https://outrageous-horny-giraffe.loca.lt"
GCP_TASKS_EAGER_EXECUTE = False
GCP_TASKS_REGION = "europe-west1"
GCP_TASKS_RESOURCE_PREFIX = "django-gcp"


client = google.cloud.storage.Client()
gcs_bucket = client.get_bucket(GCP_STORAGE_MEDIA["bucket_name"])
ddcu_bucket_identifier = register_gcs_bucket(gcs_bucket)
