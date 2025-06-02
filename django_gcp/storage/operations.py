from contextlib import contextmanager
import datetime
import logging

from django.test.utils import override_settings
from django.utils import timezone
from google.cloud.exceptions import NotFound, PreconditionFailed
from google.cloud.storage.blob import Blob

from django_gcp.exceptions import AttemptedOverwriteError, MissingBlobError

logger = logging.getLogger(__name__)

UNLIMITED_MAX_SIZE = 0


def blob_exists(bucket, blob_name):
    """Quick check that a blob with a given name exists in a bucket"""
    blob = bucket.blob(blob_name)
    return blob.exists()


def upload_blob(
    instance,
    field_name,
    local_path,
    destination_path=None,
    attributes=None,
    allow_overwrite=False,
    existing_path=None,
):
    """Upload a file to the cloud store, using the instance and field name to determine the store details

    You might use this utility to upload fixtue files for integration tests, as part of
    a migration, or as part of a function creating local files. The field's own logic for generating paths
    is used by default, although this can be overridden.

    Returns the field value so you can use this to construct instances directly:

    # Directly set the instance field without processing the blob ingress
    with override_settings(GCP_STORAGE_OVERRIDE_BLOBFIELD_VALUE=True):
        instance.field_name = upload_blob(...)

    :param django.db.Model instance: An instance of a django Model which has a BlobField
    :param str field_name: The name of the BlobField attribute on the instance
    :param str local_path: The path to the file to upload
    :param str destination_path: The path to upload the file to. If None, the remote path will be generated
    from the BlobField. If setting this value, take care to override the value of the field on the instance
    so it's path matches; this is not updated for you.
    :param dict attributes: A dictionary of attributes to set on the blob eg content type
    :param bool allow_overwrite: If true, allows existing blobs at the path to be overwritten. If destination_path is not given, this is provided to the get_destination_path callback (and may be overridden by that callback per its specification)
    :param str existing_path: If destination_path is None, this is provided to the get_destination_path callback to simulate behaviour where there is an existing path
    """
    # Get the field (which
    field = instance._meta.get_field(field_name)
    if destination_path is None:
        destination_path, allow_overwrite = field.get_destination_path(
            instance,
            original_name=local_path,
            attributes=attributes,
            existing_path=existing_path,
            temporary_path=None,
            allow_overwrite=allow_overwrite,
            bucket=field.storage.bucket,
        )

    # If not allowing overwrite, set generation matching constraints to prevent it
    if_generation_match = None if allow_overwrite else 0

    # Attributes must be a dict by default
    attributes = attributes or {}

    # Upload the file
    Blob(destination_path, bucket=field.storage.bucket).upload_from_filename(
        local_path, if_generation_match=if_generation_match, **attributes
    )

    # Return the field value
    return {"path": destination_path}


def copy_blob(
    source_bucket,
    source_blob_name,
    destination_bucket,
    destination_blob_name,
    overwrite=False,
    move=False,
    attributes=None,
):
    """Copies or moves a blob from one bucket to another with a new name.

    :param source_bucket: The google.cloud.storage.bucket object you're copying from
    :param source_blob_name: The name of the GCS object to be copied eg "path/in/bucket/source-blob-name.txt"
    :param destination_bucket_name: The google.cloud.storage.bucket object you're copying to
    :param destination_blob_name: The name of the new GCS object eg "path/in/bucket/destination-blob-name.txt"
    :param overwrite: If True, allows an existing destination file to be overwritten
    :param move: If True, removes the source blob after copy (ie moves it rather than duplicating it)
    :param attributes: A dict of values used to update attributes of the destination blob (eg {"content_type": "image/png"})
    """

    source_blob = source_bucket.blob(source_blob_name)

    extra_args = {}
    if not overwrite:
        # Optional: set a generation-match precondition to avoid potential race conditions
        # and data corruptions. The request is aborted if the object's
        # generation number does not match your precondition. For a destination
        # object that does not yet exist, set the if_generation_match precondition to 0.
        # If the destination object already exists in your bucket, set instead a
        # generation-match precondition using its generation number.
        # There is also an `if_source_generation_match` parameter, which is not used in this example.
        destination_generation_match_precondition = 0
        extra_args["if_generation_match"] = destination_generation_match_precondition

    try:
        destination_blob = source_bucket.copy_blob(source_blob, destination_bucket, destination_blob_name, **extra_args)

        verb = "copied"
        if move:
            verb = "moved"
            source_bucket.delete_blob(source_blob_name)

        logger.info(
            "Blob %s in bucket %s %s to blob %s in bucket %s",
            source_blob_name,
            source_bucket.name,
            verb,
            destination_blob_name,
            destination_bucket.name,
        )

        if attributes is not None:
            for key, value in attributes.items():
                setattr(destination_blob, key, value)
                logger.debug("Set attribute %s to %s on destination blob %s", key, value, destination_blob_name)

            destination_blob.patch()
            logger.info("Attributes of blob %s updated", destination_blob_name)

        return destination_blob

    except NotFound as e:
        raise MissingBlobError(
            f"Could not complete copy: source blob {source_blob_name} does not exist in bucket {source_bucket.name}"
        ) from e

    except PreconditionFailed as e:
        raise AttemptedOverwriteError(
            f"Could not complete copy: blob {destination_blob_name} in bucket {destination_bucket.name} already exists (source {source_blob_name} in bucket {source_bucket.name})"
        ) from e


def delete_blob(bucket, blob_name, generation=None, ignore_missing=False):
    """Deletes a blob, with the ability to handle missing blobs

    :param bucket: The bucket object from which the blob will be deleted
    :param blob_name: The name of the blob to be deleted eg "path/in/bucket/your-object-name.txt"
    :param generation: the specific generation of a versioned blob to delete. Unless generation is passed, deletion of versioned blobs will
    simply add a time_deleted parameter to those blobs.
    :param ignore_missing: If True, attempting to delete a missing blob will pass without raising an exception.
    This option should only be used when there's a real chance that objects may already have been cleaned up
    by another process by the time you call this (to prevent race conditions). Otherwise leave False since
    failure at this point can be indicative of upstream errors in handling that blob.
    """
    try:
        bucket.delete_blob(blob_name, generation=generation)
        logger.info("Deleted blob %s from bucket %s", blob_name, bucket.name)

    except NotFound as e:
        if not ignore_missing:
            raise MissingBlobError("Could not delete blob %s from bucket %s - blob not found") from e

        logger.info("Attempted to delete blob %s from bucket %s - blob missing", blob_name, bucket.name)


def get_generations(bucket, blob_name):
    """Get blobs corresponding to all generations of an object
    TODO Work up a more useful output than simply a list of objects
    :param bucket: The bucket object from which the blob will be deleted
    :param blob_name: The name of the blob to be deleted eg "path/in/bucket/your-object-name.txt"
    """

    return list(bucket.client.list_blobs(bucket.name, versions=True, prefix=blob_name))


def get_signed_upload_url(bucket, blob_name, timedelta=None, max_size_bytes=UNLIMITED_MAX_SIZE, **kwargs):
    """Get a signed URL for uploading a blob to GCS

    :param google.cloud.storage.Bucket bucket: The bucket to which the blob will be uploaded
    :param str blob_name: Name of the blob within the bucket
    :param Union[datetime.timedelta, None] timedelta: A datetime.timedelta object representing the
    period which the upload URL should be valid for (default is 60 minutes)
    :param Union[int, None] max_size_bytes: Maximum size allowable, added to any headers that are supplied in kwargs.
    """
    if timedelta is None:
        timedelta = datetime.timedelta(minutes=60)

    blob = bucket.blob(blob_name)

    if max_size_bytes != 0:
        content_length_range = f"0,{max_size_bytes}"
        headers = kwargs.pop("headers", {})
        headers["X-Goog-Content-Length-Range"] = content_length_range
        kwargs["headers"] = headers

    return blob.generate_signed_url(expiration=timezone.now() + timedelta, method="PUT", **kwargs)


@contextmanager
def uploaded_blob(instance, field_name, local_path, destination_path=None, allow_overwrite=False, delete_on_exit=False):
    """A context manager enabling the preparation of an instance with a blob uploaded from a local path.
    Optionally override the destination path (the ultimate path of the blob within the destination bucket) and allow_overwrite parameter.

    Usage:

    ```py
    my_instance = MyModel()
    with uploaded_blob(my_instance, 'my_field', '/path/to/local/file') as field_value
        my_instance.my_field = field_value
        my_instance.save()
    ```

    """

    with override_settings(GCP_STORAGE_OVERRIDE_BLOBFIELD_VALUE=True):
        field_value = upload_blob(
            instance,
            field_name=field_name,
            local_path=local_path,
            destination_path=destination_path,
            allow_overwrite=allow_overwrite,
        )
        try:
            yield field_value
        finally:
            if delete_on_exit:
                raise NotImplementedError("Deletion on exit is not yet implemented")
