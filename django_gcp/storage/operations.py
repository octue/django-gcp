import datetime
import logging
from django.utils import timezone
from django_gcp.exceptions import AttemptedOverwriteError, MissingBlobError
from google.cloud.exceptions import NotFound, PreconditionFailed


logger = logging.getLogger(__name__)


def blob_exists(bucket, blob_name):
    """Quick check that a blob with a given name exists in a bucket"""
    blob = bucket.blob(blob_name)
    return blob.exists()


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


def get_signed_upload_url(bucket, blob_name, timedelta=None, max_size_bytes=None, **kwargs):
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
    if max_size_bytes is not None:
        content_length_range = f"0,{max_size_bytes}"
        headers = kwargs.pop("headers", {})
        headers["X-Goog-Content-Length-Range"]: content_length_range

    return blob.generate_signed_url(expiration=timezone.now() + timedelta, method="PUT", **kwargs)
