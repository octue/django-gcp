# Disables for testing:
# pylint: disable=missing-docstring
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods

# Disabled because gcloud api dynamically constructed
# pylint: disable=no-member

from datetime import datetime, timedelta
import gzip
import mimetypes
from unittest import mock
from zoneinfo import ZoneInfo

from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.utils import timezone
from google.cloud.exceptions import NotFound
from google.cloud.storage.blob import Blob

from django_gcp.storage import gcloud

UTC = ZoneInfo("UTC")


class NonSeekableContentFile(ContentFile):
    def open(self, mode=None):
        return self

    def seekable(self):
        return False

    def seek(self, pos, whence=0):
        raise AttributeError()


class GCloudTestCase(TestCase):
    def setUp(self):
        self.client_patcher = mock.patch("django_gcp.storage.gcloud.Client")
        self.client_patcher.start()

    def tearDown(self):
        self.client_patcher.stop()


class GCloudStorageTests(GCloudTestCase):
    def setUp(self):
        super().setUp()
        self.bucket_name = "test-media"
        self.filename = "test_file.txt"
        self.storage = gcloud.GoogleCloudStorage(store_key="media", bucket_name=self.bucket_name)

    def test_open_read(self):
        """
        Test opening a file and reading from it
        """
        data = b"This is some test read data."

        f = self.storage.open(self.filename)
        self.storage._client.bucket.assert_called_with(self.bucket_name)
        self.storage._bucket.get_blob.assert_called_with(self.filename)

        f.blob.download_to_file = lambda tmpfile: tmpfile.write(data)
        self.assertEqual(f.read(), data)

    def test_open_read_num_bytes(self):
        data = b"This is some test read data."
        num_bytes = 10

        f = self.storage.open(self.filename)
        self.storage._client.bucket.assert_called_with(self.bucket_name)
        self.storage._bucket.get_blob.assert_called_with(self.filename)

        f.blob.download_to_file = lambda tmpfile: tmpfile.write(data)
        self.assertEqual(f.read(num_bytes), data[0:num_bytes])

    def test_open_read_nonexistent(self):
        self.storage._bucket = mock.MagicMock()
        self.storage._bucket.get_blob.return_value = None

        self.assertRaises(FileNotFoundError, self.storage.open, self.filename)
        self.storage._bucket.get_blob.assert_called_with(self.filename)

    def test_open_read_nonexistent_unicode(self):
        filename = "ủⓝï℅ⅆℇ.txt"

        self.storage._bucket = mock.MagicMock()
        self.storage._bucket.get_blob.return_value = None

        self.assertRaises(FileNotFoundError, self.storage.open, filename)

    @mock.patch("django_gcp.storage.gcloud.Blob")
    def test_open_write(self, MockBlob):
        """
        Test opening a file and writing to it
        """
        with override_settings(GCP_STORAGE_MEDIA={"bucket_name": self.bucket_name, "default_acl": "projectPrivate"}):
            data = "This is some test write data."

            # Simulate the file not existing before the write
            self.storage._bucket = mock.MagicMock()
            self.storage._bucket.get_blob.return_value = None

            f = self.storage.open(self.filename, "wb")
            MockBlob.assert_called_with(self.filename, self.storage._bucket, chunk_size=None)

            f.write(data)
            tmpfile = f._file
            # File data is not actually written until close(), so do that.
            f.close()

            MockBlob().upload_from_file.assert_called_with(
                tmpfile,
                rewind=True,
                content_type=mimetypes.guess_type(self.filename)[0],
                predefined_acl="projectPrivate",
            )

    def test_save(self):
        data = "This is some test content."
        content = ContentFile(data)

        self.storage.save(self.filename, content)

        self.storage._client.bucket.assert_called_with(self.bucket_name)
        self.storage._bucket.get_blob().upload_from_file.assert_called_with(
            content,
            rewind=True,
            size=len(data),
            content_type=mimetypes.guess_type(self.filename)[0],
            predefined_acl=None,
        )

    def test_save2(self):
        data = "This is some test ủⓝï℅ⅆℇ content."
        filename = "ủⓝï℅ⅆℇ.txt"
        content = ContentFile(data)

        self.storage.save(filename, content)

        self.storage._client.bucket.assert_called_with(self.bucket_name)
        self.storage._bucket.get_blob().upload_from_file.assert_called_with(
            content, rewind=True, size=len(data), content_type=mimetypes.guess_type(filename)[0], predefined_acl=None
        )

    def test_save_with_default_acl(self):
        data = "This is some test ủⓝï℅ⅆℇ content."
        filename = "ủⓝï℅ⅆℇ.txt"
        content = ContentFile(data)

        with override_settings(GCP_STORAGE_MEDIA={"bucket_name": self.bucket_name, "default_acl": "publicRead"}):
            self.storage.save(filename, content)
            self.storage._client.bucket.assert_called_with(self.bucket_name)
            self.storage._bucket.get_blob().upload_from_file.assert_called_with(
                content,
                rewind=True,
                size=len(data),
                content_type=mimetypes.guess_type(filename)[0],
                predefined_acl="publicRead",
            )

    def test_delete(self):
        self.storage.delete(self.filename)

        self.storage._client.bucket.assert_called_with(self.bucket_name)
        self.storage._bucket.delete_blob.assert_called_with(self.filename)

    def test_exists(self):
        self.storage._bucket = mock.MagicMock()
        self.assertTrue(self.storage.exists(self.filename))
        self.storage._bucket.get_blob.assert_called_with(self.filename)

        self.storage._bucket.reset_mock()
        self.storage._bucket.get_blob.return_value = None
        self.assertFalse(self.storage.exists(self.filename))
        self.storage._bucket.get_blob.assert_called_with(self.filename)

    def test_exists_no_bucket(self):
        # exists('') should return False if the bucket doesn't exist
        self.storage._client = mock.MagicMock()
        self.storage._client.get_bucket.side_effect = NotFound("dang")
        self.assertFalse(self.storage.exists(""))

    def test_exists_bucket(self):
        # exists('') should return True if the bucket exists
        self.assertTrue(self.storage.exists(""))

    def test_listdir(self):
        file_names = ["some/path/1.txt", "2.txt", "other/path/3.txt", "4.txt"]
        subdir = ""

        self.storage._bucket = mock.MagicMock()
        blobs, prefixes = [], []
        for name in file_names:
            directory = name.rsplit("/", 1)[0] + "/" if "/" in name else ""
            if directory == subdir:
                blob = mock.MagicMock(spec=Blob)
                blob.name = name.split("/")[-1]
                blobs.append(blob)
            else:
                prefixes.append(directory.split("/")[0] + "/")

        return_value = mock.MagicMock()
        return_value.__iter__ = mock.MagicMock(return_value=iter(blobs))
        return_value.prefixes = prefixes
        self.storage._bucket.list_blobs.return_value = return_value

        dirs, files = self.storage.listdir("")

        self.assertEqual(len(dirs), 2)
        for directory in ["some", "other"]:
            self.assertTrue(directory in dirs, f' "{directory}" not in directory list "{dirs}".')

        self.assertEqual(len(files), 2)
        for filename in ["2.txt", "4.txt"]:
            self.assertTrue(filename in files, f' "{filename}" not in file list "{files}".')

    def test_listdir_subdir(self):
        file_names = ["some/path/1.txt", "some/2.txt"]
        subdir = "some/"

        self.storage._bucket = mock.MagicMock()
        blobs, prefixes = [], []
        for name in file_names:
            directory = name.rsplit("/", 1)[0] + "/"
            if directory == subdir:
                blob = mock.MagicMock(spec=Blob)
                blob.name = name.split("/")[-1]
                blobs.append(blob)
            else:
                prefixes.append(directory.split(subdir)[1])

        return_value = mock.MagicMock()
        return_value.__iter__ = mock.MagicMock(return_value=iter(blobs))
        return_value.prefixes = prefixes
        self.storage._bucket.list_blobs.return_value = return_value

        dirs, files = self.storage.listdir(subdir)

        self.assertEqual(len(dirs), 1)
        self.assertTrue("path" in dirs, f' "path" not in directory list "{dirs}".')

        self.assertEqual(len(files), 1)
        self.assertTrue("2.txt" in files, f' "2.txt" not in files list "{files}".')

    def test_size(self):
        size = 1234

        self.storage._bucket = mock.MagicMock()
        blob = mock.MagicMock()
        blob.size = size
        self.storage._bucket.get_blob.return_value = blob

        self.assertEqual(self.storage.size(self.filename), size)
        self.storage._bucket.get_blob.assert_called_with(self.filename)

    def test_size_no_file(self):
        self.storage._bucket = mock.MagicMock()
        self.storage._bucket.get_blob.return_value = None

        self.assertRaises(NotFound, self.storage.size, self.filename)

    def test_modified_time(self):
        naive_date = datetime(2017, 1, 2, 3, 4, 5, 678)

        aware_date = timezone.make_aware(naive_date, UTC)

        self.storage._bucket = mock.MagicMock()
        blob = mock.MagicMock()
        blob.updated = aware_date
        self.storage._bucket.get_blob.return_value = blob

        with self.settings(TIME_ZONE="UTC"):
            mt = self.storage.modified_time(self.filename)
            self.assertTrue(timezone.is_naive(mt))
            self.assertEqual(mt, naive_date)
            self.storage._bucket.get_blob.assert_called_with(self.filename)

    def test_get_modified_time(self):
        naive_date = datetime(2017, 1, 2, 3, 4, 5, 678)
        aware_date = timezone.make_aware(naive_date, UTC)

        self.storage._bucket = mock.MagicMock()
        blob = mock.MagicMock()
        blob.updated = aware_date
        self.storage._bucket.get_blob.return_value = blob

        with self.settings(TIME_ZONE="America/Montreal", USE_TZ=False):
            mt = self.storage.get_modified_time(self.filename)
            self.assertTrue(timezone.is_naive(mt))
            naive_date_montreal = timezone.make_naive(aware_date)
            self.assertEqual(mt, naive_date_montreal)
            self.storage._bucket.get_blob.assert_called_with(self.filename)

        with self.settings(TIME_ZONE="America/Montreal", USE_TZ=True):
            mt = self.storage.get_modified_time(self.filename)
            self.assertTrue(timezone.is_aware(mt))
            self.assertEqual(mt, aware_date)
            self.storage._bucket.get_blob.assert_called_with(self.filename)

    def test_get_created_time(self):
        naive_date = datetime(2017, 1, 2, 3, 4, 5, 678)
        aware_date = timezone.make_aware(naive_date, UTC)

        self.storage._bucket = mock.MagicMock()
        blob = mock.MagicMock()
        blob.time_created = aware_date
        self.storage._bucket.get_blob.return_value = blob

        with self.settings(TIME_ZONE="America/Montreal", USE_TZ=False):
            mt = self.storage.get_created_time(self.filename)
            self.assertTrue(timezone.is_naive(mt))
            naive_date_montreal = timezone.make_naive(aware_date)
            self.assertEqual(mt, naive_date_montreal)
            self.storage._bucket.get_blob.assert_called_with(self.filename)

        with self.settings(TIME_ZONE="America/Montreal", USE_TZ=True):
            mt = self.storage.get_created_time(self.filename)
            self.assertTrue(timezone.is_aware(mt))
            self.assertEqual(mt, aware_date)
            self.storage._bucket.get_blob.assert_called_with(self.filename)

    def test_modified_time_no_file(self):
        self.storage._bucket = mock.MagicMock()
        self.storage._bucket.get_blob.return_value = None

        self.assertRaises(NotFound, self.storage.modified_time, self.filename)

    def test_url_public_object(self):
        url = f"https://example.com/mah-bukkit/{self.filename}"

        with override_settings(GCP_STORAGE_MEDIA={"bucket_name": self.bucket_name, "default_acl": "publicRead"}):
            self.storage._bucket = mock.MagicMock()
            blob = mock.MagicMock()
            blob.public_url = url
            blob.generate_signed_url = "not called"
            self.storage._bucket.blob.return_value = blob

            self.assertEqual(self.storage.url(self.filename), url)
            self.storage._bucket.blob.assert_called_with(self.filename)

    def test_url_not_public_file(self):
        secret_filename = "secret_file.txt"
        self.storage._bucket = mock.MagicMock()
        blob = mock.MagicMock()
        generate_signed_url = mock.MagicMock(return_value="http://signed_url")
        blob.public_url = "http://this_is_public_url"
        blob.generate_signed_url = generate_signed_url
        self.storage._bucket.blob.return_value = blob

        url = self.storage.url(secret_filename)
        self.storage._bucket.blob.assert_called_with(secret_filename)
        self.assertEqual(url, "http://signed_url")
        blob.generate_signed_url.assert_called_with(expiration=timedelta(seconds=86400), version="v4")

    def test_url_not_public_file_with_custom_expires(self):
        expiration = timedelta(seconds=3600)
        with override_settings(GCP_STORAGE_MEDIA={"bucket_name": self.bucket_name, "expiration": expiration}):
            secret_filename = "secret_file.txt"
            self.storage._bucket = mock.MagicMock()
            blob = mock.MagicMock()
            generate_signed_url = mock.MagicMock(return_value="http://signed_url")
            blob.generate_signed_url = generate_signed_url
            self.storage._bucket.blob.return_value = blob
            url = self.storage.url(secret_filename)
            self.storage._bucket.blob.assert_called_with(secret_filename)
            self.assertEqual(url, "http://signed_url")
            blob.generate_signed_url.assert_called_with(expiration=expiration, version="v4")

    def test_custom_endpoint(self):
        with override_settings(
            GCP_STORAGE_MEDIA={
                "bucket_name": self.bucket_name,
                "custom_endpoint": "https://example.com",
                "default_acl": "publicRead",
            }
        ):
            url = f"{self.storage.settings.custom_endpoint}/{self.filename}"
            self.assertEqual(self.storage.url(self.filename), url)

        with override_settings(
            GCP_STORAGE_MEDIA={
                "bucket_name": self.bucket_name,
                "custom_endpoint": "https://example.com",
                "default_acl": "projectPrivate",
            }
        ):
            bucket_name = "hyacinth"
            self.storage._bucket = mock.MagicMock()
            blob = mock.MagicMock()
            generate_signed_url = mock.MagicMock()
            blob.bucket = mock.MagicMock()
            type(blob.bucket).name = mock.PropertyMock(return_value=bucket_name)
            blob.generate_signed_url = generate_signed_url
            self.storage._bucket.blob.return_value = blob
            self.storage.url(self.filename)
            blob.generate_signed_url.assert_called_with(
                bucket_bound_hostname=self.storage.settings.custom_endpoint,
                expiration=timedelta(seconds=86400),
                version="v4",
            )

    def test_get_available_name(self):
        with override_settings(
            GCP_STORAGE_MEDIA={
                "bucket_name": self.bucket_name,
                "file_overwrite": True,
            }
        ):
            self.assertEqual(self.storage.get_available_name(self.filename), self.filename)
            self.storage._bucket = mock.MagicMock()
            self.storage._bucket.get_blob.return_value = None
        with override_settings(
            GCP_STORAGE_MEDIA={
                "bucket_name": self.bucket_name,
                "file_overwrite": False,
            }
        ):
            self.assertEqual(self.storage.get_available_name(self.filename), self.filename)
            self.storage._bucket.get_blob.assert_called_with(self.filename)

    def test_get_available_name_unicode(self):
        filename = "ủⓝï℅ⅆℇ.txt"
        self.assertEqual(self.storage.get_available_name(filename), filename)

    def test_cache_control(self):
        data = "This is some test content."
        filename = "cache_control_file.txt"
        content = ContentFile(data)
        cache_control = "public, max-age=604800"
        with override_settings(
            GCP_STORAGE_MEDIA={
                "bucket_name": self.bucket_name,
                "file_overwrite": True,
                "object_parameters": {"cache_control": cache_control},
            }
        ):
            self.storage.save(filename, content)
            bucket = self.storage.client.bucket(self.bucket_name)
            blob = bucket.get_blob(filename)
            self.assertEqual(blob.cache_control, cache_control)

    def test_storage_save_gzipped(self):
        """
        Test saving a gzipped file
        """
        name = "test_storage_save.gz"
        content = ContentFile("I am gzip'd")
        self.storage.save(name, content)
        obj = self.storage._bucket.get_blob()
        obj.upload_from_file.assert_called_with(mock.ANY, rewind=True, size=11, predefined_acl=None, content_type=None)

    def test_storage_save_gzipped_non_seekable(self):
        """
        Test saving a gzipped file
        """
        name = "test_storage_save.gz"
        content = NonSeekableContentFile("I am gzip'd")
        self.storage.save(name, content)
        obj = self.storage._bucket.get_blob()
        obj.upload_from_file.assert_called_with(mock.ANY, rewind=True, size=11, predefined_acl=None, content_type=None)

    def test_storage_save_gzip(self):
        """
        Test saving a file with gzip enabled.
        """
        with override_settings(
            GCP_STORAGE_MEDIA={
                "bucket_name": self.bucket_name,
                "gzip": True,
            }
        ):
            name = "test_storage_save.css"
            content = ContentFile("I should be gzip'd")
            self.storage.save(name, content)
            self.storage._client.bucket.assert_called_with(self.bucket_name)
            obj = self.storage._bucket.get_blob()
            self.assertEqual(obj.content_encoding, "gzip")
            obj.upload_from_file.assert_called_with(
                mock.ANY,
                rewind=True,
                size=None,
                predefined_acl=None,
                content_type="text/css",
            )
            args, _ = obj.upload_from_file.call_args
            content = args[0]
            zfile = gzip.GzipFile(mode="rb", fileobj=content)
            self.assertEqual(zfile.read(), b"I should be gzip'd")

    def test_storage_save_gzip_twice(self):
        """
        Test saving the same file content twice with gzip enabled.
        """
        with override_settings(
            GCP_STORAGE_MEDIA={
                "bucket_name": self.bucket_name,
                "gzip": True,
            }
        ):
            name = "test_storage_save.css"
            content = ContentFile("I should be gzip'd")

            # When
            self.storage.save(name, content)
            self.storage.save("test_storage_save_2.css", content)

            # Then
            self.storage._client.bucket.assert_called_with(self.bucket_name)
            obj = self.storage._bucket.get_blob()
            self.assertEqual(obj.content_encoding, "gzip")
            obj.upload_from_file.assert_called_with(
                mock.ANY,
                rewind=True,
                size=None,
                predefined_acl=None,
                content_type="text/css",
            )
            args, _ = obj.upload_from_file.call_args
            content = args[0]
            zfile = gzip.GzipFile(mode="rb", fileobj=content)
            self.assertEqual(zfile.read(), b"I should be gzip'd")

    def test_compress_content_len(self):
        """
        Test that file returned by _compress_content() is readable.
        """
        self.storage.gzip = True
        content = ContentFile("I should be gzip'd")
        content = self.storage._compress_content(content)
        self.assertTrue(len(content.read()) > 0)

    def test_location_leading_slash(self):
        msg = "'location' option in GCP_STORAGE_ cannot begin with a leading slash. Found '/'. Use '' instead."
        with self.assertRaises(ImproperlyConfigured, msg=msg):
            with override_settings(
                GCP_STORAGE_MEDIA={
                    "bucket_name": self.bucket_name,
                    "location": "/",
                }
            ):
                self.storage.settings.check()


class GCloudStorageClassTests(GCloudTestCase):
    def test_override_settings(self):
        with override_settings(
            GCP_STORAGE_MEDIA={
                "bucket_name": "test_media",
                "location": "foo1",
            }
        ):
            storage = gcloud.GoogleCloudStorage()
            self.assertEqual(storage.settings.location, "foo1")
        with override_settings(
            GCP_STORAGE_MEDIA={
                "bucket_name": "test_media",
                "location": "foo2",
            }
        ):
            storage = gcloud.GoogleCloudStorage()
            self.assertEqual(storage.settings.location, "foo2")

    def test_override_init_argument(self):
        storage = gcloud.GoogleCloudStorage(location="foo1")
        self.assertEqual(storage.settings.location, "foo1")
        storage = gcloud.GoogleCloudStorage(location="foo2")
        self.assertEqual(storage.settings.location, "foo2")

    def test_media_storage_instantiation(self):
        storage = gcloud.GoogleCloudMediaStorage()
        self.assertEqual(storage.settings.bucket_name, "example-media-assets")

    def test_static_storage_instantiation(self):
        storage = gcloud.GoogleCloudStaticStorage()
        self.assertEqual(storage.settings.bucket_name, "example-static-assets")

    def test_instiantiation_with_store_key_raises_exception(self):
        with self.assertRaises(ValueError):
            gcloud.GoogleCloudMediaStorage(store_key="not-media")

        with self.assertRaises(ValueError):
            gcloud.GoogleCloudStaticStorage(store_key="not-static")
