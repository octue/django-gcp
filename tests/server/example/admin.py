from django.conf import settings
from django.contrib import admin as django_admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from unfold import admin as unfold_admin

from django_gcp.storage.admin import BlobFieldModelAdminMixin
from django_gcp.storage.blob_utils import get_console_url, get_signed_download_url
from tests.server.example.models import (
    ExampleBlankBlobFieldModel,
    ExampleBlobFieldModel,
    ExampleCallbackBlobFieldModel,
    ExampleMultipleBlobFieldModel,
    ExampleNeverOverwriteBlobFieldModel,
    ExamplePathValidationBlobFieldModel,
    ExampleReadOnlyBlobFieldModel,
    ExampleStorageModel,
)

# Allow switching between unfold and regular, for development purposes, by simply adding unfold to installed apps
if "unfold" in settings.INSTALLED_APPS:
    ModelAdmin = unfold_admin.ModelAdmin
    django_admin.site.unregister(User)

    #
    class UserAdmin(BaseUserAdmin, ModelAdmin):
        """Allows working with user admin for unfold and for regular django"""

    django_admin.site.register(User, UserAdmin)

else:
    ModelAdmin = django_admin.ModelAdmin

from django import forms


class DownloadAndConsoleButtonsForm(forms.ModelForm):
    """Shows how to add download and console buttons to the widget"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields["blob"].widget.download_url = get_signed_download_url(self.instance, "blob")
            self.fields["blob"].widget.console_url = get_console_url(self.instance, "blob")

    class Meta:
        model = ExampleBlobFieldModel
        fields = "__all__"


class ExampleStorageModelAdmin(ModelAdmin):
    """Demonstrates normal behaviour"""


class ExampleBlankBlobFieldModelAdmin(ModelAdmin):
    """Demonstrates direct upload behaviour where null=True, blank=True"""


class ExampleBlobFieldModelAdmin(ModelAdmin):
    """Demonstrates direct upload behaviour

    This also demonstrates the ability to add a link to the GCP console
    and a download button for the existing file.
    (Note that the GCP console link turns the "Existing cloud path" text
    into a link so there's no extra space used by another button, but it
    does look the same).
    """

    form = DownloadAndConsoleButtonsForm


class ExampleCallbackBlobFieldModelAdmin(ModelAdmin):
    """Demonstrates direct upload behaviour where an on_change callback updates the activity field"""


class ExampleMultipleBlobFieldModelAdmin(ModelAdmin):
    """Demonstrates direct upload behaviour where multiple blobfields are used"""


class ExampleNeverOverwriteBlobFieldModelAdmin(ModelAdmin):
    """Demonstrates direct upload behaviour where overwrite_mode="never"."""


class ExamplePathValidationBlobFieldModelAdmin(ModelAdmin):
    """Demonstrates direct upload behaviour where a validation error is raised in the get_destination_name callback"""


class ExampleReadOnlyBlobFieldModelAdmin(BlobFieldModelAdminMixin, ModelAdmin):
    """Demonstrates how to show a read-only blob field in the admin

    Django Admin is a nightmare when it comes to how it manages readonly
    field rendering, it decides everything is text. So we have to do a lot of
    botching. The least-difficult-to-understand way (I think) is to render
    a completely separate field with a custom widget. We've supplied a template
    to help with that (which is in itself botched because it has to work with
    django's default container).

    I made a mixin to contain the botching and simplify it a bit (see below).

    Please participate in the following issue to help move on from this point:
    https://forum.djangoproject.com/t/feature-request-discussion-custom-rendering-for-readonly-fields-in-admin/32009
    """

    # NOTE: You can't currently mix and match create_only_blob_fields and
    # read_only_blob_fields, it works but there's something in the file
    # selection that fails to work when the other field has been swapped out.
    #
    # See: https://github.com/octue/django-gcp/issues/76
    #
    # To reproduce, do this:
    # fields = ["category", "example_read_only_blob", "example_create_only_blob"]
    # create_only_blob_fields = ["example_create_only_blob"]
    # read_only_blob_fields = ["example_read_only_blob"]

    fields = ["category", "example_create_only_blob"]
    readonly_fields = []  # Dont add them to admin's readonly_fields
    create_only_blob_fields = ["example_create_only_blob"]

    # You need to do this for each of the blob fields on the model
    def example_create_only_blob__readonly(self, obj):
        return self.get_readonly_blob_widget(obj, "example_create_only_blob")

    example_create_only_blob__readonly.short_description = "Create only blob"

    # You need to do this for each of the blob fields on the model
    def example_read_only_blob__readonly(self, obj):
        return self.get_readonly_blob_widget(obj, "example_read_only_blob")

    example_read_only_blob__readonly.short_description = "Read only blob"


django_admin.site.register(ExampleStorageModel, ExampleStorageModelAdmin)
django_admin.site.register(ExampleBlobFieldModel, ExampleBlobFieldModelAdmin)
django_admin.site.register(ExampleBlankBlobFieldModel, ExampleBlankBlobFieldModelAdmin)
django_admin.site.register(ExampleCallbackBlobFieldModel, ExampleCallbackBlobFieldModelAdmin)
django_admin.site.register(ExampleNeverOverwriteBlobFieldModel, ExampleNeverOverwriteBlobFieldModelAdmin)
django_admin.site.register(ExampleMultipleBlobFieldModel, ExampleMultipleBlobFieldModelAdmin)
django_admin.site.register(ExamplePathValidationBlobFieldModel, ExamplePathValidationBlobFieldModelAdmin)
django_admin.site.register(ExampleReadOnlyBlobFieldModel, ExampleReadOnlyBlobFieldModelAdmin)
