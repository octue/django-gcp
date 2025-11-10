import os


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

DEBUG = True

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(PROJECT_DIR)

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "unfold",  # <----  COMMENT THIS OUT AND REBOOT SERVER TO DEVELOP ON ORIGINAL DJANGO ADMIN
    "django.contrib.admin",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",  # Gives us shell_plus and reset_db for manipulating the test server
    "debug_toolbar",  # Allows us to inspect SQL statements made when making queries in the admin
    "django_json_widget",  # Allows us to switch over to a json editing widget instead of our own js widgets for internal development
    "django_gcp",
    "tests.server.example",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

# Required for django_debug_toolbar
if DEBUG:
    import socket

    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips] + ["127.0.0.1", "10.0.2.2"]

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
            "debug": DEBUG,
        },
    },
]

ALLOWED_HOSTS = [
    "localhost",  # Access from your local machine
    "127.0.0.1",  # Use 127.0.0.1 for tasks emulator requests (force ipv4 instead of ipv6)
]

DATABASES = {"default": get_db_conf()}

ROOT_URLCONF = "tests.server.urls"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
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
        "verbose": {"format": "%(levelname)s %(asctime)s %(module)s %(message)s"},
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
            "class": "django_gcp.logs.GoogleStructuredLogsHandler",
        },
        "gcp_error_reporting": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django_gcp.logs.GoogleErrorReportingHandler",
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
# HERE'S HOW TO SET UP STATIC, MEDIA AND EXTRA STORAGE
# ---------------------------------------------------------------------------

# LIMIT SIZE OF BLOBFIELD UPLOADS
# This can be customized per BlobField. Default if not given is unlimited upload
# size, which is unwise if your users are not both trusted and competent
GCP_STORAGE_BLOBFIELD_MAX_SIZE_BYTES = 0  # 32 * 1024 * 1024

# MEDIA FILES
DEFAULT_FILE_STORAGE = "django_gcp.storage.GoogleCloudMediaStorage"
GCP_STORAGE_MEDIA = {"bucket_name": "example-media-assets"}
MEDIA_URL = f"https://storage.googleapis.com/{GCP_STORAGE_MEDIA['bucket_name']}/"
MEDIA_ROOT = "/media/"

# STATIC FILES (FOR USING THE CLOUD STORE)
STATICFILES_STORAGE = "django_gcp.storage.GoogleCloudStaticStorage"
GCP_STORAGE_STATIC = {"bucket_name": "example-static-assets"}
STATIC_URL = f"https://storage.googleapis.com/{GCP_STORAGE_STATIC['bucket_name']}/"
STATIC_ROOT = "/static/"

# STATIC FILES (FOR USING LOCAL STORAGE)
# DEVELOPERS ONLY - Use these alternative settings for local development of CSS files,
# to avoid collectstatic taking forever each time you change the CSS.
# STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
# STATIC_URL = "/static/"
# STATIC_ROOT = os.path.join(BASE_DIR, "static")

# EXTRA STORES
GCP_STORAGE_EXTRA_STORES = {"extra-versioned": {"bucket_name": "example-extra-versioned-assets"}}


# ---------------------------------------------------------------------------
# HERE'S HOW TO SET UP TASKS
# ---------------------------------------------------------------------------

# The region your queue(s) are in
GCP_TASKS_REGION = "europe-west1"

# Used in construction of resource names
GCP_TASKS_DELIMITER = "--"

# You can override the default queue in the task class
GCP_TASKS_DEFAULT_QUEUE_NAME = "example-primary"

# Any queues and scheduler jobs created by django-gcp will have this as a prefix/suffix
# to aid with cleanup of automatically created resources
GCP_TASKS_RESOURCE_AFFIX = "django-gcp"

# Set the domain on which the worker can receive requests.
# In production:
#    - must be a real address using https eg
# GCP_TASKS_DOMAIN = "https://worker.myapp.com"
# GCP_TASKS_EMULATOR_TARGET = None
#
# In local development:
#    - we recommend using https://github.com/aertje/cloud-tasks-emulator
#    - see django-gcp/.devcontainer/docker-compose.yml for how to setup
#    - this domain and target...
#       - sends tasks to the emulator instead of GCP
#       - routes the task directly back to the dev server
#    - you could alternatively run local worker (eg on port 8100) and route tasks there
GCP_TASKS_DOMAIN = "http://127.0.0.1:8000"
GCP_TASKS_EMULATOR_TARGET = "127.0.0.1:8123"  # Remove or set to None in production

# In local development (alternative):
#    - you can use GCP_TASKS_EAGER_EXECUTE = True
#    - this will execute tasks immediately and synchronously (as they are enqueued)
#    - no need for an emulator, but beware...
#    - strictly speaking, the code runs out of sequence (before the end
#      of the current database transaction, instead of after it) which
#      can cause race conditions if the task requires instance values that
#      have not been committed to the db yet.
GCP_TASKS_EAGER_EXECUTE = False
