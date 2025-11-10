.. _storage:

Storage
=======

This module provides helpers for working with `Google Cloud Storage <https://cloud.google.com/storage/>`_, including:

#. A django ``Storage`` class allowing django's ``FileField`` to use GCS as a storage backend. This incorporates the GCS-specific parts of `django-storages <https://django-storages.readthedocs.io/en/latest/>`_.
#. A ``BlobField`` with an associated widget to facilitate direct uploads and provide more powerful ways of working with GCS features including metadata and revisions.

.. figure:: images/direct-upload-widget.png
   :align: center
   :figclass: align-center
   :alt: Direct upload widget

   The widget provides a better user experience for blankable and overwriting options.


Installation and Authentication
-------------------------------
First, follow the instructions to :ref:`install <getting_started>`, :ref:`authenticate <authentication>` and (if necessary) :ref:`set your project <projects>`.

Create bucket(s)
----------------
This library doesn't create buckets for you: infrastructure operations should be kept separate and dealt with using
tools built for the purpose, like terraform or Deployment Manager.

If you're setting up for the first time and don't want to get into that kind of infrastructure-as-code stuff, then
manually create two buckets in your project:

- One with **object-level** permissions for **media** files.
- One with **uniform, public** permissions for **static** files.

.. TIP::
    Having two buckets like this means it's easier to configure which files are public and which aren't.
    Plus, you can serve your static files much more efficiently - `publicly shared files are cached in google's
    cloud CDN <https://cloud.google.com/appengine/docs/standard/go/serving-static-files#serving_files_from>`_,
    so they're lightning quick for users to download, and egress costs you amost nothing.

.. TIP::
    To make it easy and consistent to set up (and remember which is which!), we always use kebab case for our bucket names in the form:

    .. code-block::

       <app>-<purpose>-<environment>-<media-or-static>

    The buckets for a staging environment in one of our apps look like this:

    .. figure:: images/buckets.png
        :align: center
        :figclass: align-center
        :alt: Buckets configuration

Setup Media and Static Storage
------------------------------

The most common types of storage are for media and static files, using the storage backend.
We provide custom storage classes for each, making it easier to configure them.

In your ``settings.py`` file, configure the ``STORAGES`` setting (Django 5.1+):

.. code-block:: python

    STORAGES = {
        "default": {
            "BACKEND": "django_gcp.storage.GoogleCloudMediaStorage",
            "OPTIONS": {
                "bucket_name": "app-assets-environment-media",
                "base_url": "https://storage.googleapis.com/app-assets-environment-media/",
            },
        },
        "staticfiles": {
            "BACKEND": "django_gcp.storage.GoogleCloudStaticStorage",
            "OPTIONS": {
                "bucket_name": "app-assets-environment-static",
                "base_url": "https://storage.googleapis.com/app-assets-environment-static/",
            },
        },
    }

.. note::
   The ``base_url`` option specifies the URL prefix for accessing files. If you omit it,
   Django will use the ``MEDIA_URL`` setting for the 'default' storage and ``STATIC_URL``
   for the 'staticfiles' storage. Using ``base_url`` in OPTIONS keeps all storage
   configuration in one place and prevents URL/bucket_name drift.

   You can customise the base URLs to use your own CDN, eg ``https://static.example.com/``


Migrating from Django <5.1
---------------------------

If you're upgrading from an earlier version of django-gcp that used Django <5.1, you'll need to migrate your settings
from the old ``DEFAULT_FILE_STORAGE``, ``STATICFILES_STORAGE``, and ``GCP_STORAGE_*`` format to the new ``STORAGES`` format.

**Before (Django <5.1):**

.. code-block:: python

    DEFAULT_FILE_STORAGE = "django_gcp.storage.GoogleCloudMediaStorage"
    GCP_STORAGE_MEDIA = {
        "bucket_name": "my-media-bucket",
        "location": "media/",
    }

    STATICFILES_STORAGE = "django_gcp.storage.GoogleCloudStaticStorage"
    GCP_STORAGE_STATIC = {
        "bucket_name": "my-static-bucket",
    }

    GCP_STORAGE_EXTRA_STORES = {
        "versioned": {
            "bucket_name": "my-versioned-bucket",
        }
    }

**After (Django 5.1+):**

.. code-block:: python

    STORAGES = {
        "default": {
            "BACKEND": "django_gcp.storage.GoogleCloudMediaStorage",
            "OPTIONS": {
                "bucket_name": "my-media-bucket",
                "base_url": "https://storage.googleapis.com/my-media-bucket/",
                "location": "media/",
            },
        },
        "staticfiles": {
            "BACKEND": "django_gcp.storage.GoogleCloudStaticStorage",
            "OPTIONS": {
                "bucket_name": "my-static-bucket",
                "base_url": "https://storage.googleapis.com/my-static-bucket/",
            },
        },
        "versioned": {
            "BACKEND": "django_gcp.storage.GoogleCloudStorage",
            "OPTIONS": {
                "bucket_name": "my-versioned-bucket",
                "base_url": "https://storage.googleapis.com/my-versioned-bucket/",
            },
        },
    }

Key changes:

- ``DEFAULT_FILE_STORAGE`` → ``STORAGES["default"]["BACKEND"]``
- ``STATICFILES_STORAGE`` → ``STORAGES["staticfiles"]["BACKEND"]``
- ``GCP_STORAGE_MEDIA`` → ``STORAGES["default"]["OPTIONS"]``
- ``GCP_STORAGE_STATIC`` → ``STORAGES["staticfiles"]["OPTIONS"]``
- ``GCP_STORAGE_EXTRA_STORES`` → additional entries in ``STORAGES`` dict
- ``MEDIA_URL``/``STATIC_URL`` → ``base_url`` in ``OPTIONS`` (recommended to keep config in one place)

**BlobField store_key changes:**

If you use ``BlobField`` in your models, you must update the ``store_key`` parameter:

- ``store_key="media"`` → ``store_key="default"``
- ``store_key="static"`` → ``store_key="staticfiles"``
- Extra stores now use the STORAGES alias directly (e.g., ``store_key="versioned"`` matches ``STORAGES["versioned"]``)

Example:

.. code-block:: python

    # OLD
    blob = BlobField(store_key="media", ...)

    # NEW
    blob = BlobField(store_key="default", ...)

Note that project-level settings like ``GCP_PROJECT_ID`` and ``GCP_CREDENTIALS`` remain at the root level of your settings file.


Default and Extra stores
------------------------

.. tabs::

   .. group-tab:: Extra Stores

      Any number of extra stores can be added, each corresponding to a different bucket in GCS.

      Simply add additional entries to the ``STORAGES`` dict. Each storage alias can be used to identify
      the storage backend you want to use. In your ``settings.py``:

      .. code-block:: python

         STORAGES = {
             "default": {
                 "BACKEND": "django_gcp.storage.GoogleCloudMediaStorage",
                 "OPTIONS": {
                     "bucket_name": "my-media-bucket",
                     "base_url": "https://storage.googleapis.com/my-media-bucket/",
                 },
             },
             "staticfiles": {
                 "BACKEND": "django_gcp.storage.GoogleCloudStaticStorage",
                 "OPTIONS": {
                     "bucket_name": "my-static-bucket",
                     "base_url": "https://storage.googleapis.com/my-static-bucket/",
                 },
             },
             "my-fun-store": {
                 "BACKEND": "django_gcp.storage.GoogleCloudStorage",
                 "OPTIONS": {
                     "bucket_name": "all-the-fun-datafiles",
                     "base_url": "https://storage.googleapis.com/all-the-fun-datafiles/",
                 },
             },
             "my-sad-store": {
                 "BACKEND": "django_gcp.storage.GoogleCloudStorage",
                 "OPTIONS": {
                     "bucket_name": "all-the-sad-datafiles",
                     "base_url": "https://storage.googleapis.com/all-the-sad-datafiles/",
                 },
             },
         }

      For extra stores, you can access them using ``BlobField(store_key="my-fun-store")`` or by
      using ``storages["my-fun-store"]`` in your code.


   .. group-tab:: Default Storage

      Once you're done, default_storage will be your Google Cloud Media Storage:

      .. code-block:: python

         >>> from django.core.files.storage import default_storage
         >>> print(default_storage.__class__)
         <class 'django_gcp.storage.GoogleCloudMediaStorage'>

      This way, if you define a new FileField, it will use that storage bucket:

      .. code-block:: python

         >>> from django.db import models
         >>> class MyModel(models.Model):
         ...     my_file_field = models.FileField(upload_to='pdfs')
         ...     my_image_field = models.ImageField(upload_to='photos')
         ...
         >>> obj1 = MyModel()
         >>> print(resume.pdf.storage)
         <django_gcp.storage.GoogleCloudMediaStorage object at ...>

.. _blobfield_storage:

BlobField Storage
-----------------

The benefit of a BlobField is that you can do direct upload of objects to the cloud.

This allows you to accept uploads of files > 32mb whilst on request-size-limited services like Cloud Run.

To enable this and other advanced features (like caching of metadata and blob version tracking),
``BlobField``s intentionally don't maintain the ``FileField`` api. Under the hood,
a BlobField is actually a `JSONField` allowing properties other than just the blob name to be stored in the database.

We'll flesh out these instructions later (or Pull requests accepted!) but in the meantime,
see the `example implementation here <https://github.com/octue/django-gcp/blob/main/tests/server/example/models.py>`_.

You'll need to:

#. Add a `django_gcp.storage.fields.BlobField` field to a model.
#. Define a `get_destination_path` callback to generate the eventual name of the blob in the store.

.. TIP::
   On upload, blobs are always ingressed to a temporary location then moved to their eventual destination on save of
   the model. Two steps (ingress -> rename) seems unnecessary, but this allows the eventual destination to use
   the other model fields. It also avoids problems where you require deterministic object names: where object
   versioning or retention is enabled on your bucket, an unrelated failure in
   the model ``save()`` process will prevent future uploads to the same pathname.

.. WARNING::
   Migrating from an existing ``FileField`` to a ``BlobField`` is possible but a bit tricky.
   We provide an example of how to do that migration in the example server model (see the instructions in the model, and the corresponding migration files)


FileField Storage
-----------------

Works as a standard drop-in storage backend.

.. tabs::

   .. group-tab:: File Access

      Standard file access options are available, and work as expected

      .. code-block:: python

         >>> default_storage.exists('storage_test')
         False
         >>> file = default_storage.open('storage_test', 'w')
         >>> file.write('storage contents')
         >>> file.close()

         >>> default_storage.exists('storage_test')
         True
         >>> file = default_storage.open('storage_test', 'r')
         >>> file.read()
         'storage contents'
         >>> file.close()

         >>> default_storage.delete('storage_test')
         >>> default_storage.exists('storage_test')
         False

   .. group-tab:: Models and FileFields

      An object without a file has limited functionality

      .. code-block:: python

         >>> obj1 = MyModel()
         >>> obj1.my_file_field
         <FieldFile: None>
         >>> obj1.my_file_field.size
         Traceback (most recent call last):
         ...
         ValueError: The 'my_file_field' attribute has no file associated with it.

      Saving a file enables full functionality

      .. code-block:: python

         >>> obj1.my_file_field.save('django_test.txt', ContentFile('content'))
         >>> obj1.my_file_field
         <FieldFile: tests/django_test.txt>
         >>> obj1.my_file_field.size
         7
         >>> obj1.my_file_field.read()
         'content'

      Files can be read in a little at a time, if necessary

      .. code-block:: python

         >>> obj1.my_file_field.open()
         >>> obj1.my_file_field.read(3)
         'con'
         >>> obj1.my_file_field.read()
         'tent'
         >>> '-'.join(obj1.my_file_field.chunks(chunk_size=2))
         'co-nt-en-t'

      Save another file with the same name

      .. code-block:: python

         >>> obj2 = MyModel()
         >>> obj2.my_file_field.save('django_test.txt', ContentFile('more content'))
         >>> obj2.my_file_field
         <FieldFile: tests/django_test_.txt>
         >>> obj2.my_file_field.size
         12

      Push the objects into the cache to make sure they pickle properly

      .. code-block:: python

         >>> cache.set('obj1', obj1)
         >>> cache.set('obj2', obj2)
         >>> cache.get('obj2').my_file_field
         <FieldFile: tests/django_test_.txt>


Storage Settings Options
------------------------

Each store can be set up with different options, passed within the ``OPTIONS`` dict for each storage backend in the ``STORAGES`` setting.

For example, to set the media storage up so that files go to a different location than the root of the bucket, you'd use:

.. code-block:: python

    STORAGES = {
        "default": {
            "BACKEND": "django_gcp.storage.GoogleCloudMediaStorage",
            "OPTIONS": {
                "bucket_name": "app-assets-environment-media",
                "location": "not/the/bucket/root/",
                # ... and whatever other options you want
            },
        },
    }

The full range of options (and their defaults, which apply to all stores) is as follows:

``gzip``
^^^^^^^^
Type: ``boolean``

Default: ``False``

Whether or not to enable gzipping of content types specified by ``GZIP_CONTENT_TYPES``

``gzip_content_types``
^^^^^^^^^^^^^^^^^^^^^^
Type: ``tuple``

Default: (``text/css``, ``text/javascript``, ``application/javascript``, ``application/x-javascript``, ``image/svg+xml``)

Content types which will be gzipped when ``GCP_STORAGE_IS_GZIPPED`` is ``True``

``default_acl``
^^^^^^^^^^^^^^^
Type: ``string or None``

Default: ``None``

ACL used when creating a new blob, from the
`list of predefined ACLs <https://cloud.google.com/storage/docs/access-control/lists#predefined-acl>`_.
(A "JSON API" ACL is preferred but an "XML API/gsutil" ACL will be
translated.)

For most cases, the blob will need to be set to the ``publicRead`` ACL in order for the file to be viewed.
If ``GCP_STORAGE_DEFAULT_ACL`` is not set, the blob will have the default permissions set by the bucket.

``publicRead`` files will return a public, non-expiring url. All other files return
a signed (expiring) url.

ACL Options are: ``projectPrivate``, ``bucketOwnerRead``, ``bucketOwnerFullControl``, ``private``, ``authenticatedRead``, ``publicRead``, ``publicReadWrite``

.. note::
   GCP_STORAGE_DEFAULT_ACL must be set to 'publicRead' to return a public url. Even if you set
   the bucket to public or set the file permissions directly in GCS to public.

.. note::
    When using this setting, make sure you have ``fine-grained`` access control enabled on your bucket,
    as opposed to ``Uniform`` access control, or else, file  uploads will return with HTTP 400. If you
    already have a bucket with ``Uniform`` access control set to public read, please keep
    ``GCP_STORAGE_DEFAULT_ACL`` to ``None`` and set ``GCP_STORAGE_QUERYSTRING_AUTH`` to ``False``.

``querystring_auth``
^^^^^^^^^^^^^^^^^^^^
Type: ``boolean``
Default: ``True``

If set to ``False`` it forces the url not to be signed. This setting is useful if you need to have a
bucket configured with ``Uniform`` access control configured with public read. In that case you should
force the flag ``GCP_STORAGE_QUERYSTRING_AUTH = False`` and ``GCP_STORAGE_DEFAULT_ACL = None``

``file_overwrite``
^^^^^^^^^^^^^^^^^^
Type: ``boolean``
Default: ``True``

By default files with the same name will overwrite each other. Set this to ``False`` to have extra characters appended.

``max_memory_size``
^^^^^^^^^^^^^^^^^^^
Type: ``integer``
Default: ``0`` (do not roll over)

The maximum amount of memory a returned file can take up (in bytes) before being
rolled over into a temporary file on disk. Default is 0: Do not roll over.

``blob_chunk_size``
^^^^^^^^^^^^^^^^^^^
Type: ``integer`` or ``None``
Default  ``None``

The size of blob chunks that are sent via resumable upload. If this is not set then the generated request
must fit in memory. Recommended if you are going to be uploading large files.

.. note::

   This must be a multiple of 256K (1024 * 256)

``object_parameters``
^^^^^^^^^^^^^^^^^^^^^
Type: ``dict``
Default: ``{}``

Dictionary of key-value pairs mapping from blob property name to value.

Use this to set parameters on **all** objects. To set these on a per-object
basis, subclass the backend and override ``GoogleCloudStorage.get_object_parameters``.

The valid property names are ::

  acl
  cache_control
  content_disposition
  content_encoding
  content_language
  content_type
  metadata
  storage_class

If not set, the ``content_type`` property will be guessed.

If set, ``acl`` overrides :ref:`GCP_STORAGE_DEFAULT_ACL <gs_default_acl>`.

.. warning::

   Do not set ``name``. This is set automatically based on the filename.

``custom_endpoint``
^^^^^^^^^^^^^^^^^^^
Type: ``string`` or ``None``
Default: ``None``

Sets a `custom endpoint <https://cloud.google.com/storage/docs/request-endpoints>`_,
that will be used instead of ``https://storage.googleapis.com`` when generating URLs for files.

``location``
^^^^^^^^^^^^
Type: ``string``
Default: ``""``

Subdirectory in which the files will be stored.
Defaults to the root of the bucket.

``expiration``
^^^^^^^^^^^^^^
Type: ``datetime.timedelta`` ``datetime.datetime``, ``integer`` (seconds since epoch)
Default: ``timedelta(seconds=86400)``

The time that a generated URL is valid before expiration. The default is 1 day.
Public files will return a url that does not expire. Files will be signed by
the credentials provided during :ref:`authentication <authentication>`.

The ``GCP_STORAGE_EXPIRATION`` value is handled by the underlying `Google library  <https://googlecloudplatform.github.io/google-cloud-python/latest/storage/blobs.html#google.cloud.storage.blob.Blob.generate_signed_url>`_.
It supports `timedelta`, `datetime`, or `integer` seconds since epoch time.
