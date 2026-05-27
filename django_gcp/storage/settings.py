from datetime import timedelta

from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured
from django.core.signals import setting_changed

DEFAULT_GZIP_CONTENT_TYPES = (
    "text/css",
    "text/javascript",
    "application/javascript",
    "application/x-javascript",
    "image/svg+xml",
)

DEFAULT_OBJECT_PARAMETERS = {}

DEFAULT_GCP_SETTINGS = {
    "project_id": None,
    "credentials": None,
}

DEFAULT_GCP_STORAGE_SETTINGS = {
    "bucket_name": None,
    "custom_endpoint": None,
    "location": "",
    "default_acl": None,
    "querystring_auth": True,
    "expiration": timedelta(seconds=86400),
    "gzip": False,
    "gzip_content_types": DEFAULT_GZIP_CONTENT_TYPES,
    "file_overwrite": True,
    "object_parameters": DEFAULT_OBJECT_PARAMETERS,
    "max_memory_size": 0,
    "blob_chunk_size": None,
}


class StorageSettings:
    """Combine GCP_ root settings with per-store OPTIONS from Django's STORAGES dict

    Settings are determined and cached. Initial determination is done lazily (on first setting access
    rather than on initialisation). This allows this class to be initialised prior to
    django's apps being ready.

    """

    def __init__(self, store_key, **overrides):
        setting_changed.connect(self._handle_settings_changed, dispatch_uid="ic" + str(id(self)))
        self._store_key = store_key
        self._cache = None
        self._overrides = overrides

    def __getattr__(self, setting_key):
        """Get a setting value"""

        if self._cache is None:
            self._update_settings()

        try:
            return self._cache[setting_key]
        except KeyError as e:
            raise AttributeError(f"No setting '{setting_key}' available in StorageSettings") from e

    @property
    def _stores_settings(self):
        """Get a dict of all STORAGES OPTIONS keyed by alias

        Reads from Django's STORAGES setting. Each alias in STORAGES becomes a
        store_key; the OPTIONS dict for that alias becomes the per-store config.
        """
        storages = getattr(django_settings, "STORAGES", {})
        return {alias: config.get("OPTIONS", {}) for alias, config in storages.items()}

    @property
    def _store_settings(self):
        """Dict of store settings defined in settings.py for the current store key"""
        try:
            return self._stores_settings[self._store_key]
        except KeyError as e:
            raise ImproperlyConfigured(
                f"Storage key '{self._store_key}' not found in the STORAGES setting. "
                f"Available aliases: {sorted(self._stores_settings.keys())}. "
                f"Did you forget to add '{self._store_key}' to STORAGES, or rename a legacy "
                f"'media'/'static' store_key to 'default'/'staticfiles'?"
            ) from e

    def _handle_settings_changed(self, **kwargs):
        # Invalidate lazily so we only re-resolve on the next attribute access.
        # Migration state can hold StorageSettings instances bound to legacy store_keys
        # ("media"/"static") that aren't valid against the current STORAGES dict;
        # eager re-resolution here would crash unrelated setting overrides.
        self._cache = None

    def _update_settings(self):
        """Fetch settings from django configuration, merge with defaults and cache

        Re-run on receiving ``setting_changed`` signal from django.
        """

        # Start with the default settings
        to_cache = {
            **DEFAULT_GCP_SETTINGS,
            **DEFAULT_GCP_STORAGE_SETTINGS,
        }

        # Add GCP_ settings from settings.py (common root level settings, used by the storage module)
        for setting_key in DEFAULT_GCP_SETTINGS.keys():  # pylint: disable=consider-iterating-dictionary
            try:
                to_cache[setting_key] = getattr(django_settings, f"GCP_{setting_key.upper()}")
            except AttributeError:
                # Not defined in django settings, don't add it to the dict
                pass

        # Add GCP_STORAGE_ settings (storage-specific settings for the current store)
        for setting_key in DEFAULT_GCP_STORAGE_SETTINGS.keys():  # pylint: disable=consider-iterating-dictionary
            try:
                to_cache[setting_key] = self._store_settings[setting_key]
            except KeyError:
                pass

        # Add overrides and place in cache
        self._cache = {
            **to_cache,
            **self._overrides,
        }

        self.check()

    def check(self):
        """Check the settings on this object"""
        if self.location.startswith("/"):
            correct = self.location.lstrip("/\\")
            raise ImproperlyConfigured(
                f"'location' option in STORAGES['{self._store_key}']['OPTIONS'] cannot begin with a leading slash. "
                f"Found '{self.location}'. Use '{correct}' instead."
            )
