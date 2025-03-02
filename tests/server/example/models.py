from datetime import datetime
import os
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db.models import CharField, FileField, Model, UUIDField

from django_gcp.storage.fields import BlobField


# Disabled to show the argument range in the example:
# pylint: disable-next=unused-argument
def get_destination_path(
    instance,
    original_name,
    attributes,
    existing_path,
    temporary_path,
    allow_overwrite,
    bucket,
):
    """An example callback, which is provided to BlobField in order that
    you can set the eventual pathname of the uploaded blob, using other model fields
    if you wish.

    You can also alter the allow_overwrite parameter on a per-instance basis. For example,
    overwrite might universally disabled at the field level, but you could choose to
    allow overwrite where the path you determine is equal to the existing instance path.
    In most cases you'll want to pass-through the value.

    By the time this callback is executed, the file should have been successfully uploaded
    to a temporary location in GCP. This method is called in the pre_save stage,
    so if your model uses an autoincremented id that value may not be accessible - if you need
    to set filenames based on the ID then use something like a UUID as the id field for the model,
    whose value can be set a-priori to the save process.

    In this example we prefix the end path with the category and a time but really you
    can do whatever.

    Doing instance.<your-field> gives the JSON value that was submitted with the form
    so any client-side data you need for naming can be supplied via that entry (extra fields will
    be removed and not persisted to the database).

    You can even access the blob itself and read its contents if you want to,
    but beware that this is called within the request loop on the main server so we suggest
    against reading large files or processing a lot of data from them.

    Depending on the value of `overwrite_mode` set in the field definition, use of an
    existing filename may result in an error so this function should return a unique name.

    :param django.db.models.Model instance: A model instance in the pre-save state
    :param str original_name: The original name of the uploaded file
    :param Union[dict, None] attributes: The attributes, if any, that will be applied to the destination blob
    :param Union[str, None] existing_path: If saving a model instance and overwriting an existing blob, this is its path
    :param str temporary_path: The path of the temporary upload which you can use to create a
    google.cloud.storage.Blob and access its contents, in order to determine the path (not advised
    as this will likely be slow).
    :param bool overwrite_allowed: If true, then overwriting is allowed for the present operation (determined from the overwrite mode)
    :param google.cloud.storage.Bucket bucket: The google cloud bucket object which you can use to determine whether an
    object exists at the path
    """
    # Demonstrate using another field to name the object
    category = f"{instance.category}/" if instance.category is not None else ""

    # You may wish to add a timestamp, or random string to prevent collisions
    # In this case we do the very simple thing of using the original name with random prefix
    random_prefix = str(uuid4())[0:8]

    # If you attempt to overwrite while allow_overwrite is false, a server error will raise.
    # Only set allow_overwrite = True if you really, REALLY, know what you're doing!
    return f"{category}{random_prefix}-{original_name}", allow_overwrite


def get_destination_path_from_id(
    instance,
    original_name,
    attributes,
    existing_path,
    temporary_path,
    allow_overwrite,
    bucket,
):
    """A deterministic naming callback. This produces the same name for every file
    which is very helpful for figuring out what things are in your object store, but
    can have drawbacks when it comes to naming conflicts.

    Here, the name is generated using the model id but could easily use any other unique
    combination of fields in the model. Note that you can't do this with autoincrementing
    primary IDs because this callback needs to run prior to save.

    However, this can result in validation error for a range of cases - for example,
    if you have `overwrite_mode=never` then attempt to change the file, the choice of
    deterministic filename conflicts with that choice: the BlobField should be rendered
    as a read-only widget to handle this.

    This also demonstrates that it's possible to raise validation errors from
    this callback; in this case for an unknown file extension
    """
    extension = os.path.splitext(original_name)[1]
    return f"files/file-{instance.id}{extension}", allow_overwrite


def get_destination_path_and_validate(
    instance,
    original_name,
    attributes,
    existing_path,
    temporary_path,
    allow_overwrite,
    bucket,
):
    """Demonstrates validation error behaviour in the chosen naming path

    NOTE: You can use this for other kinds of validation too, raising errors
    when the file contents are invalid, for example.

    HOWEVER, in most cases, you need to be wary. Typically, you're using this
    field (instead of FileField) because the files are large and unwieldy.

    Yes, you could download the blob, open it and validate its contents but
    in most cases that would be too slow to happen within the request-response
    cycle.

    I have seen in one case someone streaming only the first few bytes of a file
    to check it had the right headers, which is a creative approach to the problem.

    In general though for validating the contents of large files, you'll want to
    have an async tasks (or series of tasks) that run after the ingress - you'll
    want to keep a set of events to store the progress of the file through the
    validation process(es) and mark it as ready once complete. This is outside the scope
    of django-gcp and is a more generic approach to building a data lake!
    """

    extension = os.path.splitext(original_name)[1]
    if extension != ".txt":
        raise ValidationError("The file needs to have a .txt extension")
    return f"files/file-{instance.id}.txt", allow_overwrite


class ExampleStorageModel(Model):
    """
    An example model containing a FileField with django's normal indirect
    uploads (ie files come via the server)
    """

    normal = FileField(upload_to="normal_uploads", blank=True, null=True)

    class Meta:
        """Metaclass defining this model to reside in the example app"""

        app_label = "example"


class ExampleBlankBlobFieldModel(Model):
    """
    As ExampleBlobFieldModel but showing blankable behaviour
    (This is mostly used for widget development and testing)
    """

    category = CharField(max_length=20, blank=True, null=True)
    blob = BlobField(
        get_destination_path=get_destination_path,
        store_key="media",
        blank=True,
        null=True,
        help_text="Shows typical behaviour of the blobfield, with name collision prevention so you should be able to change the file as many times as you like. The field is blankable (saving with no file selected should succeed).",
    )

    class Meta:
        """Metaclass defining this model to reside in the example app"""

        app_label = "example"


class ExampleBlobFieldModel(Model):
    """
    An example model containing a BlobField which uploads files via a temporary
    ingress.
    This model was started as a FileField model then migrated, so check the migrations
    to see how that worked.
    """

    # This charfield is added to demonstrate that other fields of the model can be used
    # in order to set the blob name
    category = CharField(max_length=20, blank=True, null=True)

    # Note on how to migrate from FileField (see test_storage_field_migrations.py)
    #   This was initially created with:
    #       blob = FileField(upload_to="blob_uploads", blank=True, null=True)
    #   Then the migration uses a temporary field:
    #       blob = FileField(upload_to="blob_uploads", blank=True, null=True)
    #       blob_temp = BlobField(store_key="media")
    #   Then a custom migration is used to duplicate the data (see migration 0002).
    #   Then the old field is removed (see migration 0003).
    blob = BlobField(
        get_destination_path=get_destination_path,
        store_key="media",
        help_text="Shows typical behaviour of the blobfield, with name collision prevention so you should be able to change the file as many times as you like, but it is not blankable or nullable (attempt to save with no file selected to see validation error).",
    )

    class Meta:
        """Metaclass defining this model to reside in the example app"""

        app_label = "example"


def my_on_change_callback(value, instance):
    """Demonstrate the on_change callback functionality

    This callback is changed AFTER the commit of the current transaction

    It is designed for lightweight work like triggering further processing
    tasks or sending emails, etc, which must be done only if the transaction
    succeeded.

    If you need to make a change to the model as a result of the field
    preparation which must be included in the *same* transaction as the change
    to your BlobField, you should override your model's save() method to
    achieve this in the normal way (after the model's clean() method has been called)
    and that is the recommended pattern in general.

    The model instance is available here, but in an out-of-date state, so
    if you must work with the model instance, you may have to call
    refresh_from_db on it. You will also have to save any changes you make to the
    instance.
    """
    dt = datetime.now().isoformat()
    instance.refresh_from_db()
    # The on_change is called AFTER the commit of the current transaction, so
    if value is None:
        print("You removed the blob")
        instance.activity = f"Removed blob on {dt}"
    else:
        print(f"Do something with the value {value} and instance {instance}")
        instance.activity = f"Changed blob on {dt}"
    instance.save()


class ExampleCallbackBlobFieldModel(Model):
    """
    As ExampleBlobFieldModel but showing use of the on_change callback
    (This is mostly used for widget development and testing)
    """

    category = CharField(max_length=20, blank=True, null=True)
    activity = CharField(max_length=60, blank=True, null=True)
    blob = BlobField(
        get_destination_path=get_destination_path,
        store_key="media",
        blank=True,
        null=True,
        on_change=my_on_change_callback,
        help_text="The activity should update if you change the blob then save. If you save without changing the blob, activity shouldn't be affected.",
    )

    class Meta:
        """Metaclass defining this model to reside in the example app"""

        app_label = "example"


class ExampleNeverOverwriteBlobFieldModel(Model):
    """
    As ExampleBlobFieldModel but showing behaviour when overwriting is disabled

    Note that you should be able to create a model initially, but if you were to
    edit the file and save you will get an AttemptedOverwriteError.

    This is correct and expected - your admin or widget should be rendered as
    read-only in order to prevent these exceptions occurring.
    """

    id = UUIDField(primary_key=True, default=uuid4, editable=False)
    blob = BlobField(
        get_destination_path=get_destination_path_from_id,
        store_key="media",
        overwrite_mode="never",
        help_text="You can create a model like this, but if you attempt to select a different file during update, you should see an exception. You need to override the widget to show read-only in this case.",
    )

    class Meta:
        """Metaclass defining this model to reside in the example app"""

        app_label = "example"


class ExampleMultipleBlobFieldModel(Model):
    """
    An example model containing multiple BlobFields
    This model was started as a FileField model then migrated, so check the migrations
    to see how that worked.
    """

    # This charfield is added to demonstrate that other fields of the model can be used
    # in order to set the blob name
    category = CharField(max_length=20, blank=True, null=True)

    blob1 = BlobField(
        get_destination_path=get_destination_path,
        store_key="media",
        help_text="The get_destination_path function gives these unique names",
    )
    blob2 = BlobField(
        get_destination_path=get_destination_path,
        store_key="media",
        help_text="The get_destination_path function gives these unique names",
    )
    blob3 = BlobField(
        get_destination_path=get_destination_path,
        store_key="media",
        help_text="The get_destination_path function gives these unique names",
    )

    class Meta:
        """Metaclass defining this model to reside in the example app"""

        app_label = "example"


class ExamplePathValidationBlobFieldModel(Model):
    """An ExampleBlobFieldModel but showing behaviour when a validation error is raised from get_destination_path"""

    id = UUIDField(primary_key=True, default=uuid4, editable=False)
    blob = BlobField(
        get_destination_path=get_destination_path_and_validate,
        store_key="media",
        overwrite_mode="never",
        help_text="If you upload a file that doesn't end with .txt, you should see a validation error in the admin.",
    )

    class Meta:
        """Metaclass defining this model to reside in the example app"""

        app_label = "example"


class ExampleReadOnlyBlobFieldModel(Model):
    """
    This is identical to ExampleBlobFieldModel but I've duplicated it because
    it's complicated to register the same model twice in the admin, and we want to
    show how to set up the admin with read-only fields
    """

    category = CharField(max_length=20, blank=True, null=True)

    example_read_only_blob = BlobField(
        get_destination_path=get_destination_path,
        store_key="media",
        help_text="The widget should be read-only always",
        blank=True,  # So we can demo read-only behaviour
        null=True,  # in the admin without creating blobs
    )

    example_create_only_blob = BlobField(
        get_destination_path=get_destination_path,
        store_key="media",
        help_text="The widget should be as normal for object addition, read-only in a change form",
        blank=True,  # So we can demo read-only behaviour
        null=True,  # in the admin without creating blobs
    )

    class Meta:
        """Metaclass defining this model to reside in the example app"""

        app_label = "example"
