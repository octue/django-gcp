# pylint: disable=missing-docstring

from datetime import date
import os
import tempfile
from uuid import uuid4

from django.test import SimpleTestCase, TestCase
from google.cloud import storage

from django_gcp.exceptions import AttemptedOverwriteError, MissingBlobError
from django_gcp.storage.blob_utils import get_blob
from django_gcp.storage.operations import copy_blob, delete_blob, get_generations, uploaded_blob
from tests.server.example.models import ExampleBlobFieldModel


class StorageOperationsMixin:
    """A mixin allowing TestCase to do full integration tests on GCS, with storage operations"""

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.storage_client = storage.Client()
        # Allows us to avoid cleanup overhead by having a sweeper function trigger
        # periodically to clear up test artefacts older than today,
        # and allows us to avoid race conditions by having a per-test UID.
        uid = str(uuid4()).replace("-", "")[0:8]
        today = str(date.today())
        self.test_path = f"test/{today}--{uid}/"

        # Allows us to choose either a regular or versioned bucket
        self.bucket = self.storage_client.bucket("example-media-assets")
        self.versioned_bucket = self.storage_client.bucket("example-extra-versioned-assets")

    def _prefix_blob_name(self, blob_name):
        """Adds the test prefix to a blob name"""
        return os.path.join(self.test_path, blob_name)

    def _create_test_blob(self, bucket, blob_name, content=""):
        """Create a plain text file and upload it to a blob under the test path, for test purposes"""
        blob = storage.Blob(name=blob_name, bucket=bucket)
        blob.upload_from_string(content)
        return blob

    def _create_temporary_blob(self, bucket, tmp_path=None, content=""):
        """Create a plain text file and upload it to a blob at a temporary path"""
        tmp_path = tmp_path or f"_tmp/{uuid4()}"
        blob = storage.Blob(name=tmp_path, bucket=bucket)
        blob.upload_from_string(content)
        return blob

    def _copy(self, bucket, test_name, **extras):
        source_blob_name = self._prefix_blob_name(f"{test_name}.source.txt")
        destination_blob_name = self._prefix_blob_name(f"{test_name}.destination.txt")

        source_blob = self._create_test_blob(bucket, source_blob_name)
        destination_blob = copy_blob(bucket, source_blob_name, bucket, destination_blob_name, **extras)
        return source_blob, destination_blob


class TestStorageOperations(StorageOperationsMixin, SimpleTestCase):
    """This class tests the StorageOperations module, and comprises a full
    integration test where operations are actually executed on GCS.
    """

    def test_copy_blob(self):
        """Test that a blob can be copied"""

        source_blob, destination_blob = self._copy(self.bucket, "test_copy_blob")

        # Ensure source and destination present
        self.assertTrue(source_blob.exists())
        self.assertTrue(destination_blob.exists())

    def test_move_blob(self):
        """Test that a blob can be moved"""
        source_blob, destination_blob = self._copy(self.bucket, "test_copy_blob", move=True)

        # Ensure source gone and destination present
        self.assertFalse(source_blob.exists())
        self.assertTrue(destination_blob.exists())

    def test_copy_blob_allows_overwrite(self):
        """Test that a blob can be overwritten if allowed"""

        source_blob_name = self._prefix_blob_name("test_copy_blob_allows_overwrite.to_overwrite.txt")
        destination_blob_name = self._prefix_blob_name("test_copy_blob_allows_overwrite.to_be_overwritten.txt")

        self._create_test_blob(self.bucket, source_blob_name, "to overwrite")
        self._create_test_blob(self.bucket, destination_blob_name, "to be overwritten")
        destination_blob = copy_blob(self.bucket, source_blob_name, self.bucket, destination_blob_name, overwrite=True)

        with destination_blob.open("r") as fp:
            content = fp.read()

        self.assertEqual(content, "to overwrite")

    def test_copy_blob_prevents_overwrite(self):
        """Test that overwrite is prevented by default"""
        source_blob_name = self._prefix_blob_name("test_copy_blob_prevents_overwrite.to_overwrite.txt")
        destination_blob_name = self._prefix_blob_name("test_copy_blob_prevents_overwrite.to_be_overwritten.txt")

        self._create_test_blob(self.bucket, source_blob_name, "to overwrite")
        self._create_test_blob(self.bucket, destination_blob_name, "to be overwritten")

        with self.assertRaises(AttemptedOverwriteError):
            copy_blob(self.bucket, source_blob_name, self.bucket, destination_blob_name)

    def test_overwrite_increments_generation(self):
        """Test that overwriting a blob in a versioned store creates a new generation"""

        source_blob_name = self._prefix_blob_name("test_overwrite_increments_generation.to_overwrite.txt")
        destination_blob_name = self._prefix_blob_name("test_overwrite_increments_generation.to_be_overwritten.txt")

        self._create_test_blob(self.versioned_bucket, source_blob_name, "to overwrite")
        og_destination_blob = self._create_test_blob(self.versioned_bucket, destination_blob_name, "to be overwritten")
        destination_blob = copy_blob(
            self.versioned_bucket,
            source_blob_name,
            self.versioned_bucket,
            destination_blob_name,
            overwrite=True,
        )

        with destination_blob.open("r") as fp:
            content = fp.read()

        self.assertEqual(content, "to overwrite")
        self.assertNotEqual(og_destination_blob.generation, destination_blob.generation)

    def test_copy_blob_handles_missing(self):
        """Test that overwrite is prevented by default"""

        source_blob_name = self._prefix_blob_name("test_copy_blob_prevents_overwrite.to_overwrite.txt")
        destination_blob_name = self._prefix_blob_name("test_copy_blob_prevents_overwrite.to_be_overwritten.txt")

        with self.assertRaises(MissingBlobError):
            copy_blob(self.bucket, source_blob_name, self.bucket, destination_blob_name)

    def test_delete_blob(self):
        """Test that deletion works"""
        blob_name = self._prefix_blob_name("test_delete_blob.to_delete.txt")
        blob = self._create_test_blob(self.bucket, blob_name)
        self.assertTrue(blob.exists())
        delete_blob(self.bucket, blob_name)
        self.assertFalse(blob.exists())

    def test_delete_versioned_blob(self):
        """Test that deletion works as intended on versioned objects
        In versioned objects, the blob should record when it was deleted.
        Only if passed a specific generation number should the blob actually be removed
        """
        # Prepare a blob for deletion
        blob_name = self._prefix_blob_name("test_delete_versioned_blob.to_delete.txt")
        blob = self._create_test_blob(self.versioned_bucket, blob_name)
        self.assertTrue(blob.exists())
        self.assertIsNone(blob.time_deleted)

        # Delete the versioned blob, without specifying generation...
        delete_blob(self.versioned_bucket, blob_name)
        blob.reload()
        self.assertIsNotNone(blob.time_deleted)

        # Repeat, specifying generation to ensure removal of the actual object...
        delete_blob(self.versioned_bucket, blob_name, generation=blob.generation)
        self.assertFalse(blob.exists())

    def test_delete_missing_blob(self):
        """Test that deletion works in the event of a missing blob"""
        blob_name = self._prefix_blob_name("test_delete_missing_blob.txt")
        # Don't create the blob in cloud, just locally so we can use the exists() method
        blob = storage.Blob(name=blob_name, bucket=self.bucket)
        self.assertFalse(blob.exists())
        delete_blob(self.bucket, blob_name, ignore_missing=True)
        self.assertFalse(blob.exists())
        with self.assertRaises(MissingBlobError):
            delete_blob(self.bucket, blob_name)

    def test_get_generations(self):
        blob_name = self._prefix_blob_name("test_get_generations.txt")
        first_version = self._create_test_blob(
            self.versioned_bucket,
            blob_name,
            content="first generation",
        )
        second_version = self._create_test_blob(
            self.versioned_bucket,
            blob_name,
            content="second generation",
        )
        blobs = get_generations(self.versioned_bucket, blob_name)
        generations = [blob.generation for blob in blobs]
        self.assertEqual(len(generations), 2)
        self.assertIn(first_version.generation, generations)
        self.assertIn(second_version.generation, generations)


class TestStorageOperationsWithDatabase(StorageOperationsMixin, TestCase):
    def test_uploaded_blob(self):
        """Ensure that test_uploaded_blob will upload a blob and leave it there"""

        # Create a local file to upload
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, "test_file.txt")
            with open(local_path, "w"):
                pass  # Create an empty file

            self.assertTrue(os.path.exists(local_path))

            # Test with no destination path
            instance = ExampleBlobFieldModel()
            field_name = "blob"
            with uploaded_blob(instance, field_name, local_path) as value:
                instance.blob = value
                instance.save()
            assert get_blob(instance, "blob").exists()

            # Test with a file-like
            instance = ExampleBlobFieldModel()
            field_name = "blob"
            with open(local_path, "rb") as local_fp:
                with uploaded_blob(instance, field_name, local_fp) as value:
                    instance.blob = value
                    instance.save()
            assert get_blob(instance, "blob").exists()

            # Test raises exception on not implemented yet
            with self.assertRaises(NotImplementedError):
                instance2 = ExampleBlobFieldModel()
                with uploaded_blob(instance2, field_name, local_path, delete_on_exit=True) as value:
                    instance2.blob = value
                    instance2.save()
