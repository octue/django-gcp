# Disables for testing:
# pylint: disable=missing-docstring
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods
# pylint: disable=no-member
from unittest.mock import patch
from uuid import uuid4

from django import forms
from django.contrib.auth.models import User
from django.db import transaction
from django.test import Client, TestCase, TransactionTestCase, override_settings

from django_gcp.exceptions import MissingBlobError
from django_gcp.storage.blob_utils import get_blob
from tests.server.example.models import (
    ExampleBlankBlobFieldModel,
    ExampleBlobFieldModel,
    ExampleCallbackBlobFieldModel,
    ExampleUpdateAttributesBlobFieldModel,
)

from ._utils import get_admin_add_view_url, get_admin_change_view_url
from .test_storage_operations import StorageOperationsMixin


class BlobForm(forms.ModelForm):
    """Dummy form for testing modeladmin"""

    class Meta:
        model = ExampleBlobFieldModel
        fields = ["blob"]


class BlankBlobForm(forms.ModelForm):
    """Dummy form for testing modeladmin"""

    class Meta:
        model = ExampleBlankBlobFieldModel
        fields = ["blob"]


class CallbackBlobForm(forms.ModelForm):
    """Dummy form for testing modeladmin"""

    class Meta:
        model = ExampleCallbackBlobFieldModel
        fields = ["blob"]


class UpdateAttributesBlobForm(forms.ModelForm):
    """Dummy form for testing modeladmin"""

    class Meta:
        model = ExampleUpdateAttributesBlobFieldModel
        fields = ["blob"]


class BlobModelFactoryMixin:
    def _create(self, Model, name=None, content="", **create_kwargs):
        """Through the ORM, we may need to create blobs directly at the destination"""
        with override_settings(GCP_STORAGE_ALLOW_PATH_OVERRIDE=True):
            if name is not None:
                blob_name = self._prefix_blob_name(name)
                self._create_test_blob(self.bucket, blob_name, content)
                blob = {"path": blob_name}
            else:
                blob = None
            obj = Model.objects.create(blob=blob, **create_kwargs)
            obj.save()
        return obj


def get_destination_path_for_test(
    instance,
    original_name,
    attributes,
    existing_path,
    temporary_path,
    allow_overwrite,
    bucket,
):
    """Returns a consistent destination path for a blob for test purposes"""
    category = f"{instance.category}/" if instance.category is not None else ""
    return f"{category}{original_name}", allow_overwrite


class TestBlobFieldAdmin(StorageOperationsMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        """Set up data for the whole test case (used within the outer transaction to increase speed)"""
        User.objects.create_superuser(username="superuser", password="secret", email="admin@example.com")

    def setUp(self, *args, **kwargs):
        """Log in the superuser"""
        super().setUp(*args, **kwargs)
        self.client = Client()
        self.client.login(username="superuser", password="secret")

    def test_add_view_loads_normally(self):
        response = self.client.get(get_admin_add_view_url(ExampleBlobFieldModel))
        self.assertEqual(response.status_code, 200)

    def test_add_view_has_presigned_url(self):
        """The add view must have a presigned URL available in the context for uploading to a temporary path"""
        response = self.client.get(get_admin_add_view_url(ExampleBlobFieldModel))
        self.assertEqual(response.status_code, 200)
        widget = response.context_data["adminform"].fields["blob"].widget
        self.assertTrue(hasattr(widget, "signed_ingress_url"))
        self.assertTrue(
            widget.signed_ingress_url.startswith("https://storage.googleapis.com/example-media-assets/_tmp")
        )

    def test_full_clean_executes_in_overridden_context(self):
        """Ensure that full_clean() can be legitimately called
        on a model while in an overridden context
        """

        blob_name = self._prefix_blob_name("test_full_clean_executes_in_overridden_context.txt")
        self._create_test_blob(self.bucket, blob_name, "")
        with override_settings(GCP_STORAGE_OVERRIDE_BLOBFIELD_VALUE=True):
            obj = ExampleBlobFieldModel(blob={"path": blob_name})
            obj.full_clean()
            obj.save()

    @override_settings(GCP_STORAGE_OVERRIDE_BLOBFIELD_VALUE=True)
    def test_change_view_loads_normally(self):
        """Ensure we can load a change view"""

        blob_name = self._prefix_blob_name("test_change_view_loads_normally.txt")
        self._create_test_blob(self.bucket, blob_name, "")
        obj = ExampleBlobFieldModel.objects.create(blob={"path": blob_name})

        # Assert that the view loads
        response = self.client.get(get_admin_change_view_url(obj))
        self.assertEqual(response.status_code, 200)

        # Assert the widget contents
        widget = response.context_data["adminform"].fields["blob"].widget
        self.assertTrue(hasattr(widget, "signed_ingress_url"))
        self.assertTrue(
            widget.signed_ingress_url.startswith("https://storage.googleapis.com/example-media-assets/_tmp")
        )


class TestBlobField(StorageOperationsMixin, TestCase):
    """Inherits from transaction test case, because we use an on_commit
    hook to move ingressed files once a database save has been made

    """

    def test_validates_name_is_present_on_add(self):
        """Ensure that a ValidationError is raised if no 'name' property is present in the blob data"""

        form = BlobForm(data={"blob": {"_tmp_path": "something"}})

        self.assertEqual(
            form.errors["blob"],
            [
                "Both `_tmp_path` and `name` properties must be present in data for ExampleBlobFieldModel.blob if ingressing a new blob."
            ],
        )

    def test_validates_path_not_present_on_add(self):
        """Ensure that a ValidationError is raised if no 'name' property is present in the blob data"""

        form = BlobForm(
            data={
                "blob": {
                    "name": "something",
                    "_tmp_path": "something",
                    "path": "something",
                }
            }
        )

        self.assertEqual(
            form.errors["blob"],
            ["You cannot specify a path directly"],
        )

    def test_validates_tmp_path_is_present_on_add(self):
        """Ensure that a ValidationError is raised if no 'name' property is present in the blob data"""

        form = BlobForm(data={"blob": {"name": "something"}})

        self.assertEqual(
            form.errors["blob"],
            [
                "Both `_tmp_path` and `name` properties must be present in data for ExampleBlobFieldModel.blob if ingressing a new blob."
            ],
        )

    def test_validates_raises_on_add_blank_dict(self):
        form = BlobForm(data={"blob": {}})
        self.assertEqual(
            form.errors["blob"],
            ["This field is required."],
        )

    def test_validates_raises_on_add_blank_string(self):
        form = BlobForm(data={"blob": ""})

        self.assertEqual(
            form.errors["blob"],
            ["This field is required."],
        )

    def test_validates_raises_on_add_blank_none(self):
        form = BlobForm(data={"blob": None})

        self.assertEqual(
            form.errors["blob"],
            ["This field is required."],
        )

    @override_settings(GCP_STORAGE_OVERRIDE_BLOBFIELD_VALUE=True)
    def test_create_object_succeeds_with_overridden_path(self):
        """Through the ORM, we may need to create blobs directly at the destination"""

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            blob_name = self._prefix_blob_name("create_object_succeeds_with_overridden_path.txt")
            self._create_test_blob(self.bucket, blob_name)
            ExampleBlobFieldModel.objects.create(blob={"path": blob_name})

        # There should be no callback executed when the blob field value is overwritten directly
        self.assertEqual(len(callbacks), 0)
        count = ExampleBlobFieldModel.objects.count()
        self.assertEqual(count, 1)

    def test_create_object_fails_with_missing_blob(self):
        """Create an object but fail to copy the blob (because it's missing) then check that
        no database record was created"""
        with self.assertRaises(MissingBlobError):
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                ExampleBlobFieldModel.objects.create(
                    blob={"_tmp_path": f"_tmp/{uuid4()}.txt", "name": "missing_blob.txt"}
                )
            self.assertEqual(len(callbacks), 1)
            count = ExampleBlobFieldModel.objects.count()
            self.assertEqual(count, 0)


class TestBlankBlobField(BlobModelFactoryMixin, StorageOperationsMixin, TransactionTestCase):
    """Inherits from transaction test case, because we use an on_commit
    hook to move ingressed files once a database save has been made

    TODO REMOVE TRANSACTION TEST CASE
    as per https://code.djangoproject.com/ticket/30457
    ```
    with self.captureOnCommitCallbacks(execute=True) as callbacks:
        with transaction.atomic():
            transaction.on_commit(branch_1)
    ```
    """

    def test_validates_on_add_blank_dict(self):
        form = BlankBlobForm(data={"blob": {}})
        self.assertNotIn("blob", form.errors)

    def test_validates_on_add_blank_string(self):
        form = BlankBlobForm(data={"blob": ""})
        self.assertNotIn("blob", form.errors)

    def test_validates_on_add_blank_none(self):
        form = BlankBlobForm(data={"blob": None})
        self.assertNotIn("blob", form.errors)

    @override_settings(GCP_STORAGE_OVERRIDE_GET_DESTINATION_PATH_CALLBACK=get_destination_path_for_test)
    def test_update_valid_to_blank(self):
        # Create a valid instance
        name = self._prefix_blob_name("update_valid_to_blank.txt")
        tmp_blob = self._create_temporary_blob(self.bucket)
        form = BlankBlobForm(data={"blob": {"_tmp_path": tmp_blob.name, "name": name}})
        instance = form.save()

        # Create a form to change this instance and set the data blank
        form = BlankBlobForm(instance=instance, data={"blob": {}})
        self.assertTrue(form.is_valid())
        form.save()
        instance.refresh_from_db()
        self.assertIsNone(instance.blob)

    @override_settings(GCP_STORAGE_OVERRIDE_GET_DESTINATION_PATH_CALLBACK=get_destination_path_for_test)
    def test_update_blank_to_valid(self):
        # Create a blank instance
        form = BlankBlobForm(data={"blob": {}})
        instance = form.save()
        instance.refresh_from_db()

        name = self._prefix_blob_name("update_blank_to_valid.txt")
        tmp_blob = self._create_temporary_blob(self.bucket)

        # Create a form to change this instance and set the data to a real value
        form = BlankBlobForm(instance=instance, data={"blob": {"_tmp_path": tmp_blob.name, "name": name}})
        self.assertTrue(form.is_valid())
        form.save()
        instance.refresh_from_db()
        self.assertIsNotNone(instance.blob)
        self.assertIn("path", instance.blob)
        self.assertEqual(instance.blob["path"], name)

    @override_settings(GCP_STORAGE_OVERRIDE_GET_DESTINATION_PATH_CALLBACK=get_destination_path_for_test)
    def test_update_valid_to_valid(self):
        # Create a valid instance
        name = self._prefix_blob_name("update_valid_to_valid.txt")
        tmp_blob = self._create_temporary_blob(self.bucket)
        form = BlankBlobForm(data={"blob": {"_tmp_path": tmp_blob.name, "name": name}})
        instance = form.save()
        instance.refresh_from_db()

        new_name = self._prefix_blob_name("overwrite_update_valid_to_valid.txt")
        tmp_blob = self._create_temporary_blob(self.bucket)

        # Create a form to change this instance and set the data to a real value
        form = BlankBlobForm(
            instance=instance,
            data={"blob": {"_tmp_path": tmp_blob.name, "name": new_name}},
        )
        self.assertTrue(form.is_valid())
        form.save()
        instance.refresh_from_db()
        self.assertIsNotNone(instance.blob)
        self.assertIn("path", instance.blob)
        self.assertEqual(instance.blob["path"], new_name)

    @override_settings(GCP_STORAGE_OVERRIDE_GET_DESTINATION_PATH_CALLBACK=get_destination_path_for_test)
    def test_update_valid_unchanged(self):
        # Create a valid instance
        name = self._prefix_blob_name("update_valid_unchanged.txt")
        tmp_blob = self._create_temporary_blob(self.bucket)
        form = BlankBlobForm(data={"blob": {"_tmp_path": tmp_blob.name, "name": name}})
        instance = form.save()
        instance.refresh_from_db()
        self.assertIsNotNone(instance.blob)
        self.assertIn("path", instance.blob)
        self.assertEqual(instance.blob["path"], name)

        # Create a form to update the instance but leave the blobfield unchanged
        form = BlankBlobForm(instance=instance, data={"blob": {"path": name}, "category": "test"})
        self.assertTrue(form.is_valid())
        form.save()


class TestCallableBlobField(BlobModelFactoryMixin, StorageOperationsMixin, TestCase):
    """Test the callbacks functionality.
    Use normal test case, allowing on_commit hook to execute.
    """

    @override_settings(GCP_STORAGE_OVERRIDE_GET_DESTINATION_PATH_CALLBACK=get_destination_path_for_test)
    def test_on_change_callback_execution(self):
        with patch("django.db.transaction.on_commit") as mock_on_commit:
            with transaction.atomic():
                # Create a blank instance
                form = CallbackBlobForm(data={"blob": {}})
                instance = form.save()
                instance.refresh_from_db()

                self.assertEqual(mock_on_commit.call_count, 1)

                # Editing while keeping field blank should not execute the callback
                form = CallbackBlobForm(instance=instance, data={"blob": {}})
                instance = form.save()
                self.assertEqual(mock_on_commit.call_count, 1)

                # Editing from blank to valid should execute the callback
                name = self._prefix_blob_name("test_on_change_callback_execution.txt")
                tmp_blob = self._create_temporary_blob(self.bucket)
                form = CallbackBlobForm(
                    instance=instance,
                    data={"blob": {"_tmp_path": tmp_blob.name, "name": name}},
                )
                instance = form.save()
                self.assertEqual(mock_on_commit.call_count, 2)

                # Editing with unchanged valid entry should not trigger a callback
                form = CallbackBlobForm(instance=instance, data={"blob": {"path": name}, "category": "test"})
                form.save()
                self.assertEqual(mock_on_commit.call_count, 2)

                # Editing to a new valid entry should trigger callback
                name = self._prefix_blob_name("test_on_change_callback_execution_2.txt")
                tmp_blob = self._create_temporary_blob(self.bucket)
                form = CallbackBlobForm(
                    instance=instance,
                    data={"blob": {"_tmp_path": tmp_blob.name, "name": name}},
                )
                instance = form.save()
                self.assertEqual(mock_on_commit.call_count, 3)

                # Editing valid to blank should trigger callback
                form = CallbackBlobForm(
                    instance=instance,
                    data={"blob": {}},
                )
                instance = form.save()
                self.assertEqual(mock_on_commit.call_count, 4)

    @override_settings(GCP_STORAGE_OVERRIDE_GET_DESTINATION_PATH_CALLBACK=get_destination_path_for_test)
    def test_update_attributes_callback_execution(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            tmp_blob = self._create_temporary_blob(self.bucket)
            name = self._prefix_blob_name("test_attribute_error.txt")

            obj = ExampleUpdateAttributesBlobFieldModel.objects.create(
                category="test", blob={"_tmp_path": tmp_blob.name, "name": name}
            )

            # Callbacks are executed now at the end of this context manager

        obj.refresh_from_db()
        self.assertEqual(len(callbacks), 1)
        blob = get_blob(obj, "blob")
        self.assertEqual(blob.metadata["category"], "test")
        self.assertEqual(blob.content_type, "image/png")


class TestModelBlobField(BlobModelFactoryMixin, StorageOperationsMixin, TestCase):
    """Extra tests for corner cases and model behaviour"""

    def test_no_corruption_with_multiple_models(self):
        """Tests for the presence of a nasty corner case where
        multiple models loaded into memory at once would conflict in
        their behaviour when determining the existing_path
        """

        blob_name_1 = self._prefix_blob_name("no_corruption_1.txt")
        blob_name_2 = self._prefix_blob_name("no_corruption_2.txt")
        # self._create_test_blob(self.bucket, blob_name_1, "")
        # self._create_test_blob(self.bucket, blob_name_2, "")

        # Create two instances
        with override_settings(GCP_STORAGE_OVERRIDE_BLOBFIELD_VALUE=True):
            obj_1 = ExampleBlobFieldModel.objects.create(blob={"path": blob_name_1})
            obj_1.save()
            # In the captured behaviour, the cache of the second instance overwrite the first
            obj_2 = ExampleBlobFieldModel.objects.create(blob={"path": blob_name_2})
            obj_2.save()

        # Edit the first, without changing the KMZ field (and outside the settings override)
        new_obj_1 = ExampleBlobFieldModel.objects.get(id=obj_1.id)
        new_obj_1.category = "test-change"

        # Note this is not a blankable model, and the observed flaw in flushing
        # the cache in this case manifests in passing a None value instead of
        # the correct existing path being passed through. This save() thus
        # resulted in an IntegrityError.
        new_obj_1.save()
        self.assertEqual(new_obj_1.blob["path"], blob_name_1)
