.. _cloud_run

=========
Cloud Run
=========

.. _metadata:

Metadata
========

The `container contract for Google Cloud Run <https://cloud.google.com/run/docs/container-contract#metadata-server>`_
specifies an internal server for metadata about the running service. This is useful for:

- determining if your app is running on Cloud Run or somewhere else,
- fetching values like the ``project_id`` which are required for structured logging
- generating tokens that can be used to sign blobs without a private key.

To avoid the need to write requests to the internal server yet again, ``django_gcp``
provides a wrapper class for those query, exposing the results as properties.
See :class:`django_gcp.metadata.metadata.CloudRunMetadata`.

.. code-block:: python

   from django_gcp.metadata import CloudRunMetadata

   meta = CloudRunMetadata()

   # On your local machine, `meta.is_cloud_run` will be False, and accessing these
   # attributes will raise a NotOnCloudRunError
   if meta.is_cloud_run:
       print(meta.project_id)
       print(meta.project_number)
       print(meta.region)
       print(meta.compute_instance_id)
       print(meta.email)
       print(meta.token)
