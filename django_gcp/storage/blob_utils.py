from contextlib import contextmanager
from datetime import timedelta
from os.path import split, splitext
from tempfile import NamedTemporaryFile


def get_path(instance, field_name):
    """Get the path of the blob in the object store"""
    field_value = getattr(instance, field_name)
    return field_value.get("path", None) if field_value is not None else None


def _get_current_path(instance, field_name):
    """Get the path of the blob currently backing the field value

    Unlike ``get_path``, this resolves the temporary ingress path (``_tmp_path``)
    where the field value carries an upload that has not yet been saved, so the
    blob contents can be accessed before the blob is moved to its destination.
    When updating a saved instance with a fresh upload, ``path`` and ``_tmp_path``
    coexist; the ingress path takes precedence because it holds the incoming content.
    """
    field_value = getattr(instance, field_name)
    if field_value is None:
        return None
    return field_value.get("_tmp_path", None) or field_value.get("path", None)


def get_blob(instance, field_name, reload=True):
    """Get a blob from a model instance containing a BlobField

    This resolves only the saved (destination) path of the field; it does not resolve
    the temporary ingress path of an upload prior to save (use ``blob_to_temporary_file``
    to access incoming content).

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


@contextmanager
def blob_to_temporary_file(instance, field_name):
    """Download the file behind a BlobField to a temporary file on the server

    Yields an open binary file (a ``NamedTemporaryFile`` whose name preserves the blob's
    extension) positioned at the start of the content, or None if the field is blank.
    The file is deleted on exiting the context.

    Before the model instance is saved, the field value refers to the temporary ingress
    path, and content is downloaded from there. This enables validation of an uploaded
    file prior to saving the model (and uploading via a BlobField rather than a FileField
    avoids the request-size limits of services like Cloud Run). For example:

    ```py
    with blob_to_temporary_file(mymodel, "my_field_name") as f:
        if f is not None:
            validate_contents(f)
    ```

    :param django.db.Model instance: An instance of a django Model which has a BlobField
    :param str field_name: The name of the BlobField attribute on the instance
    """
    path = _get_current_path(instance, field_name)
    if path is None:
        yield None
    else:
        field = instance._meta.get_field(field_name)
        blob = field.storage.bucket.blob(path)
        with NamedTemporaryFile(suffix=splitext(path)[-1]) as temporary_file:
            blob.download_to_file(temporary_file)
            temporary_file.seek(0)
            yield temporary_file


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

    def blob_to_temporary_file(self, field_name):
        """Download the file behind the given model field name to a temporary file

        A context manager; see the module-level ``blob_to_temporary_file`` for details.
        """
        return blob_to_temporary_file(self, field_name)

    def get_blob(self, field_name):
        """Get a blob object for the given model field name"""
        return get_blob(self, field_name)

    def get_blob_name(self, field_name):
        """Get blob name for the given model field name"""
        return get_blob_name(self, field_name)

    @classmethod
    def get_bucket(cls, field_name):
        return cls._meta.get_field(field_name).storage.bucket

    @classmethod
    def get_bucket_name(cls, field_name):
        return cls.get_bucket(field_name).name

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
        return get_signed_download_url(self, field_name, expiration=expiration)

    # def override_path(self, field_name, path):
    #     """Set a blobfield path manually, avoiding any quality control, checks or ingress"""
