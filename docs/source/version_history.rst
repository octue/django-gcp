.. _version_history:

===============
Version History
===============

We used to recommend people create version histories. But we now do it automatically using
our `conventional commits tools <https://github/octue/conventional-commits>`_
for completely automating code versions, release numbering and release history.

So for a full version history, check our `releases page <https://github/octue/django-gcp/releases>`_.


Breaking changes in 0.25.0
--------------------------

0.25.0 drops support for Django <5.2 and Python <3.12 and migrates storage
configuration to Django's ``STORAGES`` dict. The legacy
``DEFAULT_FILE_STORAGE``, ``STATICFILES_STORAGE``, ``GCP_STORAGE_MEDIA``,
``GCP_STORAGE_STATIC``, and ``GCP_STORAGE_EXTRA_STORES`` settings are no
longer read.

Required user actions when upgrading:

1. Replace the legacy settings with a single ``STORAGES`` dict. Each former
   extra-stores entry becomes a top-level alias under ``STORAGES`` — there
   is no separate "extra" wrapper anymore. See :ref:`storage` for the new
   format and :ref:`Configuration in 0.24 and below <storage>` for the old.
2. Rename ``BlobField(store_key="media")`` to ``BlobField(store_key="default")``
   and ``store_key="static"`` to ``store_key="staticfiles"`` in every model.
   Custom store keys keep their names.
3. Run ``python manage.py makemigrations`` to capture the ``store_key`` change
   as an ``AlterField`` migration for each affected ``BlobField``.
4. If you use ``manage.py cleanup_tmp_files <store_key>``, update the
   positional argument to the new alias name.

The unused ``django-app-settings`` dependency has also been removed.
