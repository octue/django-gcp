from datetime import timedelta
from os.path import split

from google.cloud.storage.blob import Blob


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
            allow_overwrite=allow_overwrite,
            existing_path=existing_path,
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


def get_path(instance, field_name):
    """Get the path of the blob in the object store"""
    field_value = getattr(instance, field_name)
    return field_value.get("path", None) if field_value is not None else None


def get_blob(instance, field_name):
    """Get a blob from a model instance containing a BlobField

    This allows you to download the blob to a local file. For example:

    ```py
    blob = get_blob(mymodel, "my_field_name")

    logger.info("Downloading file %s from bucket %s", blob.name, blob.bucket.name)

    # Download the blob to the temporary directory
    blob_file_name = os.path.split(blob.name)[-1]
    blob.download_to_filename(blob_file_name)
    ```

    :param django.db.Model instance: An instance of a django Model which has a BlobField
    :param str field_name: The name of the BlobField attribute on the instance
    """
    path = get_path(instance, field_name)
    if path is not None:
        field = instance._meta.get_field(field_name)
        return field.storage.bucket.blob(path)


def get_blob_name(instance, field_name):
    """Get the name of the blob including its extension (absent any path)

    The name is the object path absent any folder prefixes,
    eg if blob is located at path `mystuff/1234/myfile.txt` the name
    is `myfile.txt`
    """
    path = get_path(instance, field_name)
    if path is not None:
        return split(path)[-1]


def get_signed_url(instance, field_name, expiration=None, **kwargs):
    """Get a signed URL to the blob for the given model field name
    :param str field_name: Name of the model field (which should be a BlobField)
    :param Union[datetime.datetime|datetime.timedelta|None] expiration: Expiration date or duration for the URL. If None, duration defaults to 24hrs.
    :return str: Signed URL of the blob
    """
    expiration = expiration or timedelta(hours=24)
    blob = get_blob(instance, field_name)
    if blob is not None:
        return blob.generate_signed_url(expiration=expiration, **kwargs)


def get_signed_download_url(instance, field_name, **kwargs):
    """Gets a signed URL with the response disposition set to an attachment"""
    name = get_blob_name(instance, field_name)
    if name is not None:
        return get_signed_url(instance, field_name, **kwargs, response_disposition=f"attachment; filename={name}")


def get_console_url(instance, field_name):
    """Gets the URL of the blob in the GCS console"""
    path = get_path(instance, field_name)
    if path is not None:
        field = instance._meta.get_field(field_name)
        bucket_name = field.storage.bucket.name
        return f"https://console.cloud.google.com/storage/browser/{bucket_name}/{path}"


class BlobFieldMixin:
    """Mixin to a model to provide extra utility methods for processing of blobs"""

    def get_blob(self, field_name):
        """Get a blob object for the given model field name"""
        return get_blob(self, field_name)

    def get_blob_name(self, field_name):
        """Get blob name for the given model field name"""
        return get_blob_name(self, field_name)

    def get_path(self, field_name):
        """Get the path of the blob in the object store for the given model field name"""
        return get_path(self, field_name)

    def get_signed_url(self, field_name, expiration=None):
        """Get a signed URL to the blob for the given model field name"""
        return get_signed_url(self, field_name, expiration)
