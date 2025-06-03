from datetime import timedelta
from os.path import split


def get_path(instance, field_name):
    """Get the path of the blob in the object store"""
    field_value = getattr(instance, field_name)
    return field_value.get("path", None) if field_value is not None else None


def get_blob(instance, field_name, reload=True):
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
    :param bool reload: Default True. If it is not essential to have up-to-date information from the store, speed up the call to get_blob using call with reload_blob=False
    """
    path = get_path(instance, field_name)
    if path is not None:
        field = instance._meta.get_field(field_name)
        blob = field.storage.bucket.blob(path)
        if reload:
            blob.reload()

        return blob


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

    @classmethod
    def get_bucket(cls, field_name):
        return cls._meta.get_field(field_name).storage.bucket

    def get_console_url(self, field_name):
        """Get a URL to where the file resides in GCP cloud console"""
        return get_console_url(self, field_name)

    def get_path(self, field_name):
        """Get the path of the blob in the object store for the given model field name"""
        return get_path(self, field_name)

    def get_signed_url(self, field_name, expiration=None):
        """Get a signed URL to the blob for the given model field name"""
        return get_signed_url(self, field_name, expiration)

    def get_signed_download_url(self, field_name, expiration=None):
        """Get a signed URL to the blob with the response disposition set"""
        return get_signed_download_url(self, field_name, expiration)
