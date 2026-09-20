# Disables for testing:
# pylint: disable=missing-docstring
# pylint: disable=protected-access

from datetime import timedelta
import os
from unittest.mock import patch

from django.test import TestCase, override_settings

from django_gcp.storage.blob_utils import BlobFieldMixin, blob_to_temporary_file
from tests.server.example.models import ExampleBlankBlobFieldModel, ExampleBlobFieldModel

from .test_storage_operations import StorageOperationsMixin


class MixinExampleBlobFieldModel(BlobFieldMixin, ExampleBlobFieldModel):
    """Proxy of the example model to exercise BlobFieldMixin methods"""

    class Meta:
        proxy = True
        app_label = "example"


class TestBlobToTemporaryFile(StorageOperationsMixin, TestCase):
    """Integration tests for getting the file behind a BlobField onto the server
    (https://github.com/octue/django-gcp/issues/56)
    """

    def _create_saved_instance(self, blob_name, content):
        """Create a model instance whose blob is already at its destination path"""
        self._create_test_blob(self.bucket, blob_name, content)
        with override_settings(GCP_STORAGE_OVERRIDE_BLOBFIELD_VALUE=True):
            return ExampleBlobFieldModel.objects.create(blob={"path": blob_name}, category="test")

    def test_yields_content_of_saved_blob(self):
        blob_name = self._prefix_blob_name("test_yields_content_of_saved_blob.txt")
        obj = self._create_saved_instance(blob_name, "hello local")

        with blob_to_temporary_file(obj, "blob") as f:
            local_path = f.name
            self.assertTrue(os.path.exists(local_path))
            self.assertEqual(f.read(), b"hello local")

        # The temporary file is removed on exiting the context
        self.assertFalse(os.path.exists(local_path))

    def test_temporary_file_preserves_extension(self):
        """The temporary file name keeps the blob's extension so that
        extension-sensitive validators and libraries work on it
        """
        blob_name = self._prefix_blob_name("test_temporary_file_preserves_extension.csv")
        obj = self._create_saved_instance(blob_name, "a,b\n1,2\n")

        with blob_to_temporary_file(obj, "blob") as f:
            self.assertTrue(f.name.endswith(".csv"))

    def test_yields_none_for_blank_field(self):
        obj = ExampleBlankBlobFieldModel.objects.create(blob=None)
        with blob_to_temporary_file(obj, "blob") as f:
            self.assertIsNone(f)

    def test_yields_content_of_ingressed_blob_before_save(self):
        """Before the model is saved, the field value refers to the temporary
        ingress path; the helper must download from there so uploads can be
        validated prior to saving the model
        """
        tmp_blob = self._create_temporary_blob(self.bucket, content="uploaded but not yet saved")
        obj = ExampleBlobFieldModel(blob={"_tmp_path": tmp_blob.name, "name": "pre_save.txt"}, category="test")

        with blob_to_temporary_file(obj, "blob") as f:
            self.assertEqual(f.read(), b"uploaded but not yet saved")

    def test_ingressed_blob_takes_precedence_over_saved_blob(self):
        """When updating a saved instance with a fresh upload, the field value carries
        both the saved path and the temporary ingress path; the helper must yield the
        incoming content, not the stale saved content
        """
        blob_name = self._prefix_blob_name("test_ingress_precedence.txt")
        obj = self._create_saved_instance(blob_name, "old content")

        tmp_blob = self._create_temporary_blob(self.bucket, content="new content")
        obj.blob = {"path": blob_name, "_tmp_path": tmp_blob.name, "name": "test_ingress_precedence.txt"}

        with blob_to_temporary_file(obj, "blob") as f:
            self.assertEqual(f.read(), b"new content")


class TestBlobFieldMixin(StorageOperationsMixin, TestCase):
    """Tests for BlobFieldMixin methods on a model instance"""

    def _create_saved_instance(self, blob_name, content=""):
        self._create_test_blob(self.bucket, blob_name, content)
        with override_settings(GCP_STORAGE_OVERRIDE_BLOBFIELD_VALUE=True):
            return MixinExampleBlobFieldModel.objects.create(blob={"path": blob_name}, category="test")

    def test_blob_to_temporary_file(self):
        blob_name = self._prefix_blob_name("test_mixin_blob_to_temporary_file.txt")
        obj = self._create_saved_instance(blob_name, "mixin content")

        with obj.blob_to_temporary_file("blob") as f:
            self.assertEqual(f.read(), b"mixin content")

    def test_get_signed_download_url_with_expiration(self):
        """Regression test: the mixin previously passed expiration positionally into a
        keyword-only signature, raising TypeError
        """
        blob_name = self._prefix_blob_name("test_mixin_get_signed_download_url.txt")
        obj = self._create_saved_instance(blob_name)
        expiration = timedelta(minutes=5)

        with patch("google.cloud.storage.Blob.generate_signed_url", return_value="http://signed") as signed:
            url = obj.get_signed_download_url("blob", expiration=expiration)

        self.assertEqual(url, "http://signed")
        signed.assert_called_once_with(
            expiration=expiration,
            response_disposition=f"attachment; filename={os.path.split(blob_name)[-1]}",
        )
