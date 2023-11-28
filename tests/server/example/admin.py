from django.conf import settings
from django.contrib import admin as django_admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from unfold import admin as unfold_admin

from tests.server.example.models import (
    ExampleBlankBlobFieldModel,
    ExampleBlobFieldModel,
    ExampleMultipleBlobFieldModel,
    ExampleStorageModel,
    ExampleUneditableBlobFieldModel,
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


class ExampleStorageModelAdmin(ModelAdmin):
    """A basic admin panel to demonstrate normal storage behaviour"""


class ExampleBlobFieldModelAdmin(ModelAdmin):
    """A basic admin panel to demonstrate the direct upload storage behaviour"""


class ExampleBlankBlobFieldModelAdmin(ModelAdmin):
    """A basic admin panel to demonstrate the direct upload storage behaviour where blank=True"""


class ExampleUneditableBlobFieldModelAdmin(ModelAdmin):
    """A basic admin panel to demonstrate the direct upload storage behaviour where blank=True"""


class ExampleMultipleBlobFieldModelAdmin(ModelAdmin):
    """A basic admin panel to demonstrate the direct upload storage behaviour where multiple blobfields are used"""


django_admin.site.register(ExampleStorageModel, ExampleStorageModelAdmin)
django_admin.site.register(ExampleBlobFieldModel, ExampleBlobFieldModelAdmin)
django_admin.site.register(ExampleBlankBlobFieldModel, ExampleBlankBlobFieldModelAdmin)
django_admin.site.register(ExampleUneditableBlobFieldModel, ExampleUneditableBlobFieldModelAdmin)
django_admin.site.register(ExampleMultipleBlobFieldModel, ExampleMultipleBlobFieldModelAdmin)
