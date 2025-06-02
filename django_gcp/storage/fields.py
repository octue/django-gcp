import json
import logging
import os
from uuid import uuid4

from django.conf import settings
from django.contrib.admin.widgets import AdminTextareaWidget
from django.core import checks
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from .forms import CloudObjectFormField
from .gcloud import GoogleCloudStorage
from .operations import UNLIMITED_MAX_SIZE, blob_exists, copy_blob, get_signed_upload_url
from .widgets import DEFAULT_ACCEPT_MIMETYPE, CloudObjectWidget

logger = logging.getLogger(__name__)

DEFAULT_OVERWRITE_MODE = "never"

OVERWRITE_MODES = [
    "never",
    "update",
    "update-versioned",
    "add",
    "add-versioned",
    "add-update",
    "add-update-versioned",
]

DEFAULT_OVERRIDE_BLOBFIELD_VALUE = False


class BlobField(models.JSONField):
    """A FileField replacement with cloud store object-specific features

    Features such as metadata fetching/synchronisation and direct uploads are enabled.

    BlobField allows storage classes to be declared in settings. This enables:
    - storages to be switched without database migrations (supporting integration
      and release preview type workflows plus cloud migration)
    - eaiser way of using different buckets for different BlobFields without
      defining a Storage class for each bucket

    BlobField is built on JSONField to allow more complex information to be stored
    and queried. Examples might include:
     - cached object generation or metageneration,
     - cached object metadata, or
     - status of direct uploads

    BlobField does not inherit directly from FileField to avoid the burden of strict
    compatibility with legacy or irrelevant-to-cloud-storage behaviour (like django
    admin overriding formfields or coping with edge cases around name and path handling).
    We do this to support a clear and maintainable implementation.

    :param ingress_to: A string defining the path within the bucket to which direct uploads
    will be ingressed. These uploaded files will be moved to their ultimate path in the store on save of the model.

    :param accept_mimetype: A string passed to widgets, suitable for use in the `accept` attribute
    of an html filepicker. This will allow you to narrow down, eg to `image/*` or an even more
    specific mimetype. No validation is done at the field level that objects actually are of this
    type (because the python mimetypes module doesn't accept wildcard mimetypes and we don't want to
    go on a wild goose chase just for this small feature).

    :param get_destination_path: A callable to determine the destination path of the blob.
    The blob should already have been successfully uploaded to the temporary location
    in GCP prior to creation of this model instance. This function is then called in the
    pre_save stage of the new model instance, so it has access to all the model fields in
    order to construct the destination filename. Note this EXCLUDES the id, if the model has an
    autoincrementing ID field that gets created on save, because that can't be known prior to
    the save.

    :param max_size_bytes: The maximum size in bytes of files that can be uploaded.

    :param overwrite_mode: One of `OVERWRITE_MODES` determining the circumstances under which overwrite
    is allowed. overwrite mode behaves as follows:
    - never: Never allows overwrite
    - update: Only when updating an object
    - update-versioned: Only when updating an object and the bucket has object versioning
    - add: Only when adding an object (we're not sure why you'd want this, here for completeness)
    - add-versioned: Only when adding an object to a versioned bucket (again, for completeness)
    - add-update: Always allow (ie when adding or updating an object)
    - add-update-versioned: When adding or updating an object to a versioned bucket

    :param on_change: A callable that will be executed on change of the field value. This will be called
    on commit of the transaction (ie once any file upload is ingressed to its final location) and allows you,
    for example, to dispatch a worker task to further process the uploaded blob.
    """

    description = _("A GCP Cloud Storage object")
    empty_values = [None, "", [], ()]

    def __init__(
        self,
        get_destination_path=None,
        ingress_to="_tmp/",
        store_key="media",
        accept_mimetype=DEFAULT_ACCEPT_MIMETYPE,
        overwrite_mode=DEFAULT_OVERWRITE_MODE,
        max_size_bytes=None,
        on_change=None,
        update_attributes=None,
        **kwargs,
    ):
        self._validated = False
        self._cleaned = False
        self._on_commit_blank = None
        self._on_commit_valid = None
        self._versioning_enabled = None
        self._temporary_path = None
        self._max_size_bytes = max_size_bytes
        self._primary_key_set_explicitly = "primary_key" in kwargs
        self._choices_set_explicitly = "choices" in kwargs
        self.overwrite_mode = overwrite_mode
        self.get_destination_path = get_destination_path
        self.update_attributes = update_attributes
        self.ingress_to = ingress_to
        self.ingress_path = None
        self.store_key = store_key
        self.accept_mimetype = accept_mimetype
        self.on_change = on_change
        kwargs["default"] = kwargs.pop("default", None)
        kwargs["help_text"] = kwargs.pop("help_text", "GCP cloud storage object")

        # Note, if you want to define overrides, then use the GCP_STORAGE_EXTRA_STORES
        # setting with a different key
        self.storage = GoogleCloudStorage(store_key=store_key)

        # We should consider if there's a good use case for customising the storage class:
        #
        # self.storage = import_string(storage_class)(store_key=store_key)
        #
        # If doing so we should also check that the resulting storage class is a subclass
        # of GoogleCloudStorage, to ensure that the storage API is compatible:
        #
        # if not isinstance(self.storage, GoogleCloudStorage):
        #     raise TypeError(
        #         "%s.storage must be a subclass/instance of %s.%s"
        #         % (
        #             self.__class__.__qualname__,
        #             GoogleCloudStorage.__module__,
        #             GoogleCloudStorage.__qualname__,
        #         )
        #     )
        super().__init__(**kwargs)

    def check(self, **kwargs):
        return [
            *super().check(**kwargs),
            *self._check_explicit(),
            *self._check_get_destination_path(),
            *self._check_update_attributes(),
            *self._check_ingress_to(),
            *self._check_overwrite_mode(),
            *self._check_on_change(),
        ]

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["store_key"] = self.store_key
        kwargs["ingress_to"] = self.ingress_to
        kwargs["accept_mimetype"] = self.accept_mimetype
        kwargs["overwrite_mode"] = self.overwrite_mode
        kwargs["get_destination_path"] = self.get_destination_path
        kwargs["update_attributes"] = self.update_attributes
        kwargs["on_change"] = self.on_change
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        widget = kwargs.pop("widget", None)
        if widget is None or issubclass(widget, AdminTextareaWidget):
            widget = CloudObjectWidget(
                accept_mimetype=self.accept_mimetype,
                signed_ingress_url=self._get_signed_ingress_url(),
                max_size_bytes=self.max_size_bytes,
                ingress_path=self._get_temporary_path(),
            )

        # Set up some defaults while letting the caller override them
        defaults = {"form_class": CloudObjectFormField, "widget": widget}
        defaults.update(kwargs)
        return super().formfield(**defaults)

    @property
    def override_blobfield_value(self):
        """Shortcut to access the GCP_STORAGE_OVERRIDE_BLOBFIELD_VALUE setting"""
        return getattr(
            settings,
            "GCP_STORAGE_OVERRIDE_BLOBFIELD_VALUE",
            DEFAULT_OVERRIDE_BLOBFIELD_VALUE,
        )

    @property
    def max_size_bytes(self):
        """Shortcut to determine the max size in bytes allowable as an upload

        Defaults to unlimited upload size (which is dangerous, but since you're
        signing a URL for the user to upload we assume you've established trust
        in the user and know what you're doing!).
        """
        if self._max_size_bytes is not None:
            return self._max_size_bytes

        return getattr(
            settings,
            "GCP_STORAGE_BLOBFIELD_MAX_SIZE_BYTES",
            UNLIMITED_MAX_SIZE,
        )

    def clean(self, value, model_instance, skip_validation=False):
        """Clean the value to ensure correct state and on_commit hooks.
        This method is called during clean_fields on model save.
        """

        # An escape hatch allowing you to set the path directly. This is dangerous and should only be done
        # explicitly for the purpose of data migration and manipulation. You should never allow an untrusted
        # client to set paths directly, because knowing the path of a pre-existing object allows you to assume
        # access to it. Tip: You can use django's override_settings context manager to set this temporarily.
        if getattr(
            settings,
            "GCP_STORAGE_OVERRIDE_BLOBFIELD_VALUE",
            DEFAULT_OVERRIDE_BLOBFIELD_VALUE,
        ):
            logger.warning(
                "Overriding %s value to %s",
                self.__class__.__name__,
                value,
            )
            new_value = value

        else:
            # Validate the value given
            if not skip_validation and not self._validated:
                self.validate(value, model_instance)

            # Clean {} --> None
            value = self._clean_blank_value(getattr(model_instance, self.attname))

            # Get model state
            add = model_instance._state.adding
            existing_path = None if add else self._get_existing_path(model_instance)

            # There are six scenarios to deal with:
            adding_blank = add and value is None
            adding_valid = add and value is not None
            updating_valid_to_valid = not add and self._get_valid_to_valid(model_instance)
            updating_valid_to_blank = not add and self._get_valid_to_blank(model_instance)
            updating_blank_to_valid = not add and self._get_blank_to_valid(model_instance)
            unchanged = not add and self._get_unchanged(model_instance)

            # Branch based on scenarios
            if unchanged:
                new_value = {"path": value["path"]} if value is not None else None

            elif adding_blank or updating_valid_to_blank:
                new_value = None

                # Trigger the on_change callback at the end of the commit when we know the
                # database transaction will work
                def on_commit_blank():
                    if self.on_change is not None:
                        self.on_change(new_value, instance=model_instance)

                # clean may happen outside transations so we must
                # actually register the transaction during pre-save,
                # store the callback here temporarily
                self._on_commit_blank = on_commit_blank

            elif adding_valid or updating_blank_to_valid or updating_valid_to_valid:
                new_value = {}

                allow_overwrite = self._get_allow_overwrite(add)

                attributes = self._update_attributes(
                    getattr(value, "attributes", {}),
                    instance=model_instance,
                    original_name=value["name"],
                    existing_path=existing_path,
                    temporary_path=value["_tmp_path"],
                    adding=add,
                    bucket=self.storage.bucket,
                )

                new_value["path"], allow_overwrite = self._get_destination_path(
                    instance=model_instance,
                    original_name=value["name"],
                    attributes=attributes,
                    allow_overwrite=self._get_allow_overwrite(add),
                    existing_path=existing_path,
                    temporary_path=value["_tmp_path"],
                    bucket=self.storage.bucket,
                )

                logger.info(
                    "Adding/updating cloud object via temporary ingress at %s to %s",
                    value["_tmp_path"],
                    new_value["path"],
                )

                # Trigger the copy only on successful commit of the transaction. We have to
                # capture the dual edge cases of the file not moving correctly, and the database
                # row not saving (eg due to validation errors in other model fields).
                # https://stackoverflow.com/questions/33180727/trigering-post-save-signal-only-after-transaction-has-completed
                def on_commit_valid():
                    copy_blob(
                        self.storage.bucket,
                        value["_tmp_path"],
                        self.storage.bucket,
                        new_value["path"],
                        move=True,
                        overwrite=allow_overwrite,
                        attributes=attributes,
                    )
                    if self.on_change is not None:
                        self.on_change(new_value, instance=model_instance)

                logger.info(
                    "Registered move of %s to %s to happen on transaction commit",
                    value["_tmp_path"],
                    new_value["path"],
                )
                self._on_commit_valid = on_commit_valid

            else:
                # Raise unknown edge cases rather than failing silently
                raise ValueError(
                    f"Unable to determine field state for {self._get_fieldname(model_instance)}. The most likely cause of this doing an operation (like migration) without setting GCP_STORAGE_OVERRIDE_BLOBFIELD_VALUE=True. Otherwise, please contact the django_gcp developers and describe what you're doing along with this exception stacktrace. Value was: {json.dumps(value)}"
                )

        # Cache DB values in the instance so you can reuse it without multiple DB queries
        # pylint: disable-next=protected-access
        model_instance._state.fields_cache[self.attname] = new_value

        self._cleaned = True

        return new_value

    def pre_save(self, model_instance, add):
        """Run on_commit hooks for transactions"""
        value = getattr(model_instance, self.attname)
        if not self._cleaned:
            value = self.clean(value, model_instance, skip_validation=True)

        if self._on_commit_blank is not None:
            transaction.on_commit(self._on_commit_blank)
            self._on_commit_blank = None

        if self._on_commit_valid is not None:
            transaction.on_commit(self._on_commit_valid)
            self._on_commit_valid = None

        # Reset the spaghetti used for meeting all django's awkward flows
        self._cleaned = False
        self._validated = False
        self._on_commit_blank = None
        self._on_commit_valid = None

        return value

    def validate(self, value, model_instance):
        """Validate field value contents
        Checks that the value is a dict and checks blankness.
        If the model is in an adding state, checks contents of the value and also presence
        of the ingressing file in the cloud store (this latter check causes an API request to the store)
        """

        # Override the superclass completely because it doesn't do anything useful
        # and has counterintuitive behaviour around what constitutes blank json
        # super().validate(value, model_instance)
        field_name = f"{model_instance.__class__.__name__}.{self.attname}"

        # Accept None or a dict
        value_or_dict = value or dict()
        if not isinstance(value_or_dict, dict):
            raise ValidationError(self.error_messages["invalid"], code="invalid", params={"value": value})

        if not self.blank and len(value_or_dict) == 0:
            raise ValidationError(self.error_messages["blank"], code="blank")

        has_tmp_path_or_name = "_tmp_path" in value_or_dict or "name" in value_or_dict
        has_tmp_path_and_name = "_tmp_path" in value_or_dict and "name" in value_or_dict
        has_path = "path" in value_or_dict
        is_blank = not has_path and not has_tmp_path_and_name
        # pylint: disable-next=protected-access
        adding = model_instance._state.adding
        updating = not adding
        blankable = self.blank
        editable = self.editable

        # Check that if a _tmp_path is given, a name is also given
        if has_tmp_path_or_name and not has_tmp_path_and_name:
            raise ValidationError(
                f"Both `_tmp_path` and `name` properties must be present in data for {field_name} if ingressing a new blob."
            )

        # Check the matrix of valid combinations with specific error messages for each
        if adding and blankable:
            # Valid values:
            #   None
            #   {"_tmp_path":"something-new", "name":"something"}
            if has_path:
                raise ValidationError("You cannot specify a path directly")
            if not is_blank and not has_tmp_path_and_name:
                raise ValidationError("Provide either a blank value or valid ingress location")

        elif adding and not blankable:
            # Valid values:
            #   {"_tmp_path":"something-new", "name":"something"}
            if has_path:
                raise ValidationError("You cannot specify a path directly")
            if not has_tmp_path_and_name:
                raise ValidationError("Provide a valid ingress location")

        elif updating and blankable and editable:
            # Valid values:
            #   None
            #   {"path":"something-unchanged-from-last"}
            #   {"_tmp_path":"something-new", "name":"something"}
            if not is_blank and not has_path and not has_tmp_path_and_name:
                raise ValidationError("Provide either a blank value, valid ingress location or the existing blob path")

        elif updating and blankable and not editable:
            # Valid values:
            #   None
            #   {"path":"something-unchanged-from-last"}
            if has_tmp_path_and_name:
                raise ValidationError("Cannot change an uneditable field")
            if not is_blank and not has_path:
                raise ValidationError("Field is not editable")

        elif updating and not blankable and editable:
            # Valid values:
            #   {"path":"something-unchanged-from-last"}
            #   {"_tmp_path":"something-new", "name":"something"}
            if not has_path and not has_tmp_path_and_name:
                raise ValidationError("Provide either a valid ingress location or the existing blob path")

        elif updating and not blankable and not editable:
            # Valid values:
            #   {"path":"something-unchanged-from-last"}
            if has_tmp_path_and_name:
                raise ValidationError("Cannot change an uneditable field")
            if not has_path:
                raise ValidationError("Provide the existing blob path")

        # Check for temporary blob completion
        if has_tmp_path_and_name:
            tmp_path = value["_tmp_path"]
            if not blob_exists(self.storage.bucket, tmp_path):
                raise ValidationError(
                    f"Upload incomplete or failed (no blob at '{tmp_path}' in bucket '{self.storage.bucket.name}')"
                )

        # Check that path roundtrips correctly without an attempt to change it
        if has_path:
            if not self.override_blobfield_value and self._get_path_altered(model_instance):
                raise ValidationError(
                    f"You cannot directly alter the `path` property in {field_name} data. Return the original `path` property to leave the field unchanged, or new `_tmp_path` and `name` properties to update the field."
                )

        self._validated = True

    @property
    def versioning_enabled(self):
        """True if object versioning is enabled on the bucket configured for this field"""
        if self._versioning_enabled is None:
            self._versioning_enabled = bool(self.storage.bucket.versioning_enabled)
        return self._versioning_enabled

    def _check_ingress_to(self):
        if isinstance(self.ingress_to, str) and self.ingress_to.startswith("/"):
            return [
                checks.Error(
                    "{self.__class__.__name__}'s 'ingress_to' argument must be a relative path, not an absolute path.",
                    obj=self,
                    id="fields.E202",
                    hint="Remove the leading slash.",
                )
            ]
        return []

    def _check_overwrite_mode(self):
        if self.overwrite_mode not in OVERWRITE_MODES:
            return [
                checks.Error(
                    "{self.__class__.__name__}'s 'overwrite_mode' is invalid",
                    obj=self,
                    id="fields.E202",
                    hint=f"Try one of: {OVERWRITE_MODES}",
                )
            ]
        return []

    def _check_explicit(self):
        if self._primary_key_set_explicitly or self._choices_set_explicitly:
            return [
                checks.Error(
                    f"'primary_key', and 'choices' are not valid arguments for a {self.__class__.__name__}",
                    obj=self,
                    id="fields.E201",
                )
            ]
        return []

    def _check_get_destination_path(self):
        if not callable(self.get_destination_path):
            return [
                checks.Error(
                    f"'get_destination_path' argument in {self.__class__.__name__} must be a callable function to return the destination object name.",
                    obj=self,
                    id="fields.E201",
                )
            ]
        return []

    def _check_update_attributes(self):
        if self.update_attributes is not None and not callable(self.update_attributes):
            return [
                checks.Error(
                    f"'update_attributes' argument in {self.__class__.__name__} must be None, or a callable function that updates attributes to be set on ingressed blobs.",
                    obj=self,
                    id="fields.E201",
                )
            ]
        return []

    def _check_on_change(self):
        if self.on_change is not None and not callable(self.on_change):
            return [
                checks.Error(
                    f"'on_change' argument in {self.__class__.__name__} must be or a callable function, or None",
                    obj=self,
                    id="fields.E201",
                )
            ]
        return []

    @staticmethod
    def _clean_blank_value(value):
        """Convert blanks values formulated as empty dicts {} to None"""
        if value is not None and len(value) == 0:
            value = None
        return value

    def _get_allow_overwrite(self, add):
        """Return a boolean determining if overwrite should be allowed for this operation"""
        mode_map = {
            "never": False,
            "update": not add,
            "update-versioned": self.versioning_enabled and not add,
            "add": add,
            "add-versioned": self.versioning_enabled and add,
            "add-update": True,
            "add-update-versioned": self.versioning_enabled,
        }
        return mode_map[self.overwrite_mode]

    def _get_blank_to_valid(self, instance):
        """Return true if overwriting a blank path with a valid one"""
        existing_path = self._get_existing_path(instance)
        temporary_path = self._get_instance_tmp_path(instance)
        return existing_path is None and temporary_path is not None

    def _get_existing_path(self, instance):
        """Gets the existing (saved in db) path; will raise an error if the instance is unsaved.
        Caches value on the instance to avoid duplicate database calls within a transaction.
        """
        # pylint: disable=protected-access
        if self.attname not in instance._state.fields_cache.keys():
            pk_name = instance._meta.pk.name
            # pylint: disable-next=protected-access
            existing = instance.__class__._default_manager.get(**{pk_name: getattr(instance, pk_name)})
            # Cache value in a dict because None is a valid value
            instance._state.fields_cache[self.attname] = getattr(existing, self.attname)
        value_or_dict = instance._state.fields_cache.get(self.attname, None) or {}
        return value_or_dict.get("path", None)

    def _get_fieldname(self, instance):
        """Return the ModelName.FieldName string for use in error messages and warnings"""
        return f"{instance.__class__.__name__}.{self.attname}"

    def _get_instance_path(self, instance):
        """Gets the instance path (or None) for a given instance"""
        value_or_dict = getattr(instance, self.attname) or {}
        return value_or_dict.get("path", None)

    def _get_instance_tmp_path(self, instance):
        """Gets the instance path (or None) for a given instance"""
        value_or_dict = getattr(instance, self.attname) or {}
        return value_or_dict.get("_tmp_path", None)

    def _get_path_altered(self, instance):
        """Return true if the path has changed between a given value and what's stored in the database.

        If there is no path in the database (e.g. a blank entry is stored) the result is False.

        Used only for validation purposes: the client side should never be able to specify the path.
        """
        existing_path = self._get_existing_path(instance)
        instance_path = self._get_instance_path(instance)

        return existing_path is not None and instance_path is not None and instance_path != existing_path

    def _get_signed_ingress_url(self):
        """Return a signed URL for uploading a blob to the temporary_path"""
        return get_signed_upload_url(
            self.storage.bucket,
            self._get_temporary_path(),
            content_type="application/octet-stream",
            max_size_bytes=self.max_size_bytes,
        )

    def _get_temporary_path(self):
        """Return a temporary path to which a blob can be uploaded before renaming"""
        if self._temporary_path is None:
            self._temporary_path = os.path.join(self.ingress_to, str(uuid4()))
        return self._temporary_path

    def _get_unchanged(self, instance):
        """Return true if the path value is simply returned unchanged with no _tmp_path"""
        existing_path = self._get_existing_path(instance)
        instance_path = self._get_instance_path(instance)
        temporary_path = self._get_instance_tmp_path(instance)
        return existing_path == instance_path and temporary_path is None

    def _get_valid_to_blank(self, instance):
        """Return true if overwriting a valid path with a blank one"""
        existing_path = self._get_existing_path(instance)
        temporary_path = self._get_instance_tmp_path(instance)
        return existing_path is not None and temporary_path is None

    def _get_valid_to_valid(self, instance):
        """Return true if updating object contents at an existing path"""
        existing_path = self._get_existing_path(instance)
        temporary_path = self._get_instance_tmp_path(instance)
        return existing_path is not None and temporary_path is not None

    def _get_destination_path(self, *args, **kwargs):
        """Call the get_destination_path callback unless an override is defined in
        settings. This funcitonality is intended for test purposes only, because
        patching the callback in a test framework is a struggle
        """
        get_destination_path = getattr(
            settings,
            "GCP_STORAGE_OVERRIDE_GET_DESTINATION_PATH_CALLBACK",
            self.get_destination_path,
        )
        return get_destination_path(*args, **kwargs)

    def _update_attributes(self, attributes, **kwargs):
        """Call the update_attributes callback unless an override is defined in
        settings. This funcitonality is intended for test purposes only, because
        patching the callback in a test framework is a struggle
        """
        update_attributes = getattr(
            settings,
            "GCP_STORAGE_OVERRIDE_UPDATE_ATTRIBUTES_CALLBACK",
            self.update_attributes,
        )
        if update_attributes is not None:
            return update_attributes(attributes, **kwargs)
        return attributes
