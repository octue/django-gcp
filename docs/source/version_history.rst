.. _version_history:

===============
Version History
===============

We used to recommend people create version histories. But we now do it automatically using
our `conventional commits tools <https://github/octue/conventional-commits>`_
for completely automating code versions, release numbering and release history.

So for a full version history, check our `releases page <https://github/octue/django-gcp/releases>`_.

Breaking Changes in Next Release
---------------------------------

**Django 5.1+ STORAGES Setting Migration**

This release drops support for Django <5.1 and migrates to Django's new ``STORAGES`` setting format.

**What changed:**

- **Minimum Django version**: Now requires Django >=5.1,<6.0 (was >=4.0,<5.1)
- **Settings format**: The old ``DEFAULT_FILE_STORAGE``, ``STATICFILES_STORAGE``, ``GCP_STORAGE_MEDIA``, ``GCP_STORAGE_STATIC``, and ``GCP_STORAGE_EXTRA_STORES`` settings are no longer supported
- **New format**: Use Django's ``STORAGES`` dict setting (introduced in Django 4.2, required in Django 5.1+)
- **BlobField store_key**: Must be updated to use Django's storage aliases (``"default"``, ``"staticfiles"``, etc.)

**Migration guide:**

See the :ref:`storage` documentation for complete migration instructions. In summary:

Old settings::

    DEFAULT_FILE_STORAGE = "django_gcp.storage.GoogleCloudMediaStorage"
    GCP_STORAGE_MEDIA = {"bucket_name": "my-media"}
    STATICFILES_STORAGE = "django_gcp.storage.GoogleCloudStaticStorage"
    GCP_STORAGE_STATIC = {"bucket_name": "my-static"}

New settings::

    STORAGES = {
        "default": {
            "BACKEND": "django_gcp.storage.GoogleCloudMediaStorage",
            "OPTIONS": {
                "bucket_name": "my-media",
                "base_url": "https://storage.googleapis.com/my-media/",
            },
        },
        "staticfiles": {
            "BACKEND": "django_gcp.storage.GoogleCloudStaticStorage",
            "OPTIONS": {
                "bucket_name": "my-static",
                "base_url": "https://storage.googleapis.com/my-static/",
            },
        },
    }

BlobField changes::

    # OLD
    blob = BlobField(store_key="media", ...)

    # NEW
    blob = BlobField(store_key="default", ...)
