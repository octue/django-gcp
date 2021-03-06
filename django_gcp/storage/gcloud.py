# TODO Remove this pylint disable and clean up methods
# pylint: disable=arguments-renamed

import mimetypes
from tempfile import SpooledTemporaryFile
from django.core.exceptions import SuspiciousOperation
from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from google.cloud.exceptions import NotFound
from google.cloud.storage import Blob, Client
from google.cloud.storage.blob import _quote

from .compress import CompressedFileMixin, CompressStorageMixin
from .settings import StorageSettings
from .utils import clean_name, get_available_overwrite_name, safe_join, setting, to_bytes


CONTENT_ENCODING = "content_encoding"
CONTENT_TYPE = "content_type"


class GoogleCloudFile(CompressedFileMixin, File):
    """A django File object representing a GCP storage object"""

    def __init__(self, name, mode, storage):  # pylint: disable=super-init-not-called
        self.name = name
        self.mime_type = mimetypes.guess_type(name)[0]
        self._mode = mode
        self._storage = storage
        self.blob = storage.bucket.get_blob(name)
        if not self.blob and "w" in mode:
            self.blob = Blob(self.name, storage.bucket, chunk_size=storage.settings.blob_chunk_size)
        self._file = None
        self._is_dirty = False

    def size(self):
        return self.blob.size

    def _get_file(self):
        if self._file is None:
            self._file = SpooledTemporaryFile(
                max_size=self._storage.settings.max_memory_size,
                suffix=".GSStorageFile",
                dir=setting("FILE_UPLOAD_TEMP_DIR"),
            )
            if "r" in self._mode:
                self._is_dirty = False
                self.blob.download_to_file(self._file)
                self._file.seek(0)
            if self._storage.settings.gzip and self.blob.content_encoding == "gzip":
                self._file = self._decompress_file(mode=self._mode, file=self._file)
        return self._file

    def _set_file(self, value):
        self._file = value

    file = property(_get_file, _set_file)

    def read(self, num_bytes=None):
        """Read from the file-like object"""
        if "r" not in self._mode:
            raise AttributeError("File was not opened in read mode.")

        if num_bytes is None:
            num_bytes = -1

        return super().read(num_bytes)

    def write(self, content):
        """Write to the file-like object"""
        if "w" not in self._mode:
            raise AttributeError("File was not opened in write mode.")
        self._is_dirty = True
        return super().write(to_bytes(content))

    def close(self):
        """Close the file-like object"""
        if self._file is not None:
            if self._is_dirty:
                blob_params = self._storage.get_object_parameters(self.name)
                self.blob.upload_from_file(
                    self.file,
                    rewind=True,
                    content_type=self.mime_type,
                    predefined_acl=blob_params.get("acl", self._storage.settings.default_acl),
                )
            self._file.close()
            self._file = None


@deconstructible
class GoogleCloudStorage(CompressStorageMixin, Storage):
    """Storage class allowing django to use GCS as an object store

    Instantiates as the `media` store by default. Pass `media`, `static` or any of the keys in"""

    def __init__(self, store_key="media", **overrides):
        super().__init__()

        self.settings = StorageSettings(store_key, **overrides)
        self._bucket = None
        self._client = None

    def get_accessed_time(self, *args, **kwargs):
        """Get the last accessed time of the file

        This value is ALWAYS None because we cannot know the last accessed time on a cloud file.

        This method is here for API compatibility with django's Storage class.
        """
        return None

    def path(self, *args, **kwargs):
        """Get the local path of the file

        This value is ALWAYS None because the path is not necessarily distinct for an object
        not on the local filesystem.

        This method is here for API compatibility with django's Storage class.
        """

    @property
    def client(self):
        """The google-storage client for this store"""
        if self._client is None:
            self._client = Client(project=self.settings.project_id, credentials=self.settings.credentials)
        return self._client

    @property
    def bucket(self):
        """The google-storage bucket object for this store"""
        if self._bucket is None:
            self._bucket = self.client.bucket(self.settings.bucket_name)
        return self._bucket

    def _normalize_name(self, name):
        """
        Normalizes the name so that paths like /path/to/ignored/../something.txt
        and ./file.txt work.  Note that clean_name adds ./ to some paths so
        they need to be fixed here. We check to make sure that the path pointed
        to is not outside the directory specified by the LOCATION setting.
        """
        try:
            return safe_join(self.settings.location, name)
        except ValueError:
            raise SuspiciousOperation("Attempted access to '%s' denied." % name)

    def _open(self, name, mode="rb"):
        name = self._normalize_name(clean_name(name))
        file_object = GoogleCloudFile(name, mode, self)
        if not file_object.blob:
            raise FileNotFoundError("File does not exist: %s" % name)
        return file_object

    def _save(self, name, content):
        cleaned_name = clean_name(name)
        name = self._normalize_name(cleaned_name)

        content.name = cleaned_name
        file_object = GoogleCloudFile(name, "rw", self)

        upload_params = {}
        blob_params = self.get_object_parameters(name)
        upload_params["predefined_acl"] = blob_params.pop("acl", self.settings.default_acl)
        upload_params[CONTENT_TYPE] = blob_params.pop(CONTENT_TYPE, file_object.mime_type)

        if (
            self.settings.gzip
            and upload_params[CONTENT_TYPE] in self.settings.gzip_content_types
            and CONTENT_ENCODING not in blob_params
        ):
            content = self._compress_content(content)
            blob_params[CONTENT_ENCODING] = "gzip"

        for prop, val in blob_params.items():
            setattr(file_object.blob, prop, val)

        file_object.blob.upload_from_file(content, rewind=True, size=getattr(content, "size", None), **upload_params)
        return cleaned_name

    def get_object_parameters(self, name):
        """Override this to return a dictionary of overwritable blob-property to value.

        Returns GS_OBJECT_PARAMETERS by default. See the docs for all possible options.
        """
        return self.settings.object_parameters.copy()

    def delete(self, name):
        name = self._normalize_name(clean_name(name))
        try:
            self.bucket.delete_blob(name)
        except NotFound:
            pass

    def exists(self, name):
        if not name:  # root element aka the bucket
            try:
                self.client.get_bucket(self.bucket)
                return True
            except NotFound:
                return False

        name = self._normalize_name(clean_name(name))
        return bool(self.bucket.get_blob(name))

    def listdir(self, name):
        name = self._normalize_name(clean_name(name))
        # For bucket.list_blobs and logic below name needs to end in /
        # but for the root path "" we leave it as an empty string
        if name and not name.endswith("/"):
            name += "/"

        iterator = self.bucket.list_blobs(prefix=name, delimiter="/")
        blobs = list(iterator)
        prefixes = iterator.prefixes

        files = []
        dirs = []

        for blob in blobs:
            parts = blob.name.split("/")
            files.append(parts[-1])
        for folder_path in prefixes:
            parts = folder_path.split("/")
            dirs.append(parts[-2])

        return list(dirs), files

    def _get_blob(self, name):
        # Wrap google.cloud.storage's blob to raise if the file doesn't exist
        blob = self.bucket.get_blob(name)

        if blob is None:
            raise NotFound(f"File does not exist: {name}")

        return blob

    def size(self, name):
        name = self._normalize_name(clean_name(name))
        blob = self._get_blob(name)
        return blob.size

    def modified_time(self, name):
        name = self._normalize_name(clean_name(name))
        blob = self._get_blob(name)
        return timezone.make_naive(blob.updated)

    def get_modified_time(self, name):
        name = self._normalize_name(clean_name(name))
        blob = self._get_blob(name)
        updated = blob.updated
        return updated if setting("USE_TZ") else timezone.make_naive(updated)

    def get_created_time(self, name):
        """
        Return the creation time (as a datetime) of the file specified by name.
        The datetime will be timezone-aware if USE_TZ=True.
        """
        name = self._normalize_name(clean_name(name))
        blob = self._get_blob(name)
        created = blob.time_created
        return created if setting("USE_TZ") else timezone.make_naive(created)

    def url(self, name):
        """
        Return public url or a signed url for the Blob.
        This DOES NOT check for existance of Blob - that makes codes too slow
        for many use cases.
        """
        name = self._normalize_name(clean_name(name))
        blob = self.bucket.blob(name)
        blob_params = self.get_object_parameters(name)
        no_signed_url = (
            blob_params.get("acl", self.settings.default_acl) == "publicRead" or not self.settings.querystring_auth
        )

        if not self.settings.custom_endpoint and no_signed_url:
            return blob.public_url
        elif no_signed_url:
            return "{storage_base_url}/{quoted_name}".format(
                storage_base_url=self.settings.custom_endpoint,
                quoted_name=_quote(name, safe=b"/~"),
            )
        elif not self.settings.custom_endpoint:
            return blob.generate_signed_url(expiration=self.settings.expiration, version="v4")
        else:
            return blob.generate_signed_url(
                bucket_bound_hostname=self.settings.custom_endpoint,
                expiration=self.settings.expiration,
                version="v4",
            )

    def get_available_name(self, name, max_length=None):
        name = clean_name(name)
        if self.settings.file_overwrite:
            return get_available_overwrite_name(name, max_length)
        return super().get_available_name(name, max_length)


class GoogleCloudMediaStorage(GoogleCloudStorage):
    """Storage whose bucket name is taken from the GCP_STORAGE_MEDIA_NAME setting

    This actually behaves exactly as a default instantitation of the base
    ``GoogleCloudStorage`` class, but is there to make configuration more
    explicit for first-timers.

    """

    def __init__(self, **overrides):
        if overrides.pop("store_key", "media") != "media":
            raise ValueError("You cannot instantiate GoogleCloudMediaStorage with a store_key other than 'media'")
        super().__init__(store_key="media", **overrides)


class GoogleCloudStaticStorage(GoogleCloudStorage):
    """Storage defined with an appended bucket name (called "<bucket>-static")

    We define that static files are stored in a different bucket than the (private) media files, which:
        1. gives us less risk of accidentally setting private files as public
        2. allows us easier visual inspection in the console of what's private and what's public static
        3. allows us to set blanket public ACLs on the static bucket
        4. makes it easier to clean up private files with no entry in the DB

    """

    def __init__(self, **overrides):
        if overrides.pop("store_key", "static") != "static":
            raise ValueError("You cannot instantiate GoogleCloudStaticStorage with a store_key other than 'static'")
        super().__init__(store_key="static", **overrides)
