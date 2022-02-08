from datetime import timedelta
from appsettings import (
    AppSettings,
    BooleanSetting,
    ObjectSetting,
    PositiveIntegerSetting,
    Setting,
    StringSetting,
    TupleSetting,
)
from django.core.exceptions import ValidationError


DEFAULT_GZIP_CONTENT_TYPES = (
    "text/css",
    "text/javascript",
    "application/javascript",
    "application/x-javascript",
    "image/svg+xml",
)

DEFAULT_OBJECT_PARAMETERS = {}


class NoLeadingSlashStringSetting(StringSetting):
    """Prevents specification of locations with a leading `/`"""

    def validate(self, value):
        if value.startswith("/") or value.startswith("\\"):
            correct = value.lstrip("/").lstrip("\\")
            raise ValidationError(
                f"{self.full_name} cannot begin with a leading slash. Found '{value}'. Use '{correct}' instead."
            )

        return value


class DjangoGCPSettings(AppSettings):
    """Settings handler for the django-gcp app

    GS_PROJECT_ID
    GS_CREDENTIALS
    GS_BUCKET_NAME
    GS_CUSTOM_ENDPOINT
    GS_LOCATION
    GS_DEFAULT_ACL
    GS_QUERYSTRING_AUTH
    GS_EXPIRATION
    GS_IS_GZIPPED
    GZIP_CONTENT_TYPES
    GS_FILE_OVERWRITE
    GS_CACHE_CONTROL
    GS_MAX_MEMORY_SIZE

    # Related settings in settings.py
    APP_INTEGER_SETTING = -24
    MY_APP_PREFIXED_SETTING = []

    # Instantiate the app settings class wherever you need to
    gcp_settings = DjangoGCPSettings()
    assert gcp_settings.querystring_auth is False  # True (default value)
    assert gcp_settings.project_id == "not-your-project"  # raises AttributeError
    assert gcp_settings.max_memory_size >= 0  # True

    # Values are cached to avoid performance issues, but cache is cleaned on
    # Django's setting_changed signal allowing for override in testing:
    with override_settings(APP_REQUIRED_SETTING="hello", APP_INTEGER_SETTING=0):
        assert appconf.required_setting == "hello"  # True
        assert appconf.named_setting < 0  # False

    # You can still access settings through the class itself (values not cached)
    print(MySettings.custom_endpoint.get_value())  # explicit call
    print(MySettings.custom_endpoint.value)  # with property

    # Run type checking and required presence on all settings at once
    DjangoGCPSettings.check()  # raises Django's ImproperlyConfigured (missing required_setting)
    # DjangoGCPSettings.check() is already called in django.apps.AppConfig's ready method, to check for valid settings on app start.
    """

    # App-wide settings
    project_id = StringSetting(default=None)
    credentials = ObjectSetting(default=None)

    # GCS settings
    bucket_name = StringSetting(prefix="gcp_storage_", default="test_bucket")
    custom_endpoint = StringSetting(prefix="gcp_storage_", default=None)
    location = NoLeadingSlashStringSetting(prefix="gcp_storage_", default="")
    default_acl = StringSetting(prefix="gcp_storage_", default=None)
    querystring_auth = BooleanSetting(prefix="gcp_storage_", default=True)
    expiration = Setting(prefix="gcp_storage_", default=timedelta(seconds=86400))
    gzip = BooleanSetting(prefix="gcp_storage_", default=False)
    gzip_content_types = TupleSetting(prefix="gcp_storage_", default=DEFAULT_GZIP_CONTENT_TYPES)
    file_overwrite = BooleanSetting(prefix="gcp_storage_", default=True)
    cache_control = StringSetting(prefix="gcp_storage_", default=None)
    object_parameters = ObjectSetting(prefix="gcp_storage_", default=DEFAULT_OBJECT_PARAMETERS)
    max_memory_size = PositiveIntegerSetting(prefix="gcp_storage_", default=0)
    blob_chunk_size = PositiveIntegerSetting(prefix="gcp_storage_", default=None)

    class Meta:
        """Defines default settings behaviour"""

        setting_prefix = "gcp_"

    def __init__(self, *args, overrides=None, **kwargs):
        self._overrides = overrides if overrides is not None else dict()
        super().__init__(*args, *kwargs)

    def __getattr__(self, item):
        if item in self._overrides.keys():
            return self._overrides[item]
        return super().__getattr__(item)
