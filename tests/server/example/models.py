from uuid import uuid4
from django.db.models import CharField, FileField, Model
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


class ExampleStorageModel(Model):
    """
    An example model containing a FileField with django's normal indirect
    uploads (ie files come via the server)
    """

    normal = FileField(upload_to="normal_uploads", blank=True, null=True)

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
    blob = BlobField(get_destination_path=get_destination_path, store_key="media")

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
    )

    class Meta:
        """Metaclass defining this model to reside in the example app"""

        app_label = "example"


class ExampleUneditableBlobFieldModel(Model):
    """
    As ExampleBlobFieldModel but showing behaviour when editable=False
    (This is mostly used for widget development and testing)
    """

    category = CharField(max_length=20, blank=True, null=True)
    blob = BlobField(get_destination_path=get_destination_path, store_key="media", editable=False)

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

    blob1 = BlobField(get_destination_path=get_destination_path, store_key="media")
    blob2 = BlobField(get_destination_path=get_destination_path, store_key="media")
    blob3 = BlobField(get_destination_path=get_destination_path, store_key="media")

    class Meta:
        """Metaclass defining this model to reside in the example app"""

        app_label = "example"


def my_on_change_callback(value, instance):
    """Demonstrate the on_change callback functionality"""
    if value is None:
        print("You removed the blob")
    else:
        print(f"Do something with the value {value} and instance {instance}")


class ExampleCallbackBlobFieldModel(Model):
    """
    As ExampleBlobFieldModel but showing use of the on_change callback
    (This is mostly used for widget development and testing)
    """

    category = CharField(max_length=20, blank=True, null=True)
    blob = BlobField(
        get_destination_path=get_destination_path,
        store_key="media",
        blank=True,
        null=True,
        on_change=my_on_change_callback,
    )

    class Meta:
        """Metaclass defining this model to reside in the example app"""

        app_label = "example"
