from django.contrib import admin

from tests.server.example.models import (
    ExampleBlankBlobFieldModel,
    ExampleBlobFieldModel,
    ExampleMultipleBlobFieldModel,
    ExampleStorageModel,
    ExampleUneditableBlobFieldModel,
)


class ExampleStorageModelAdmin(admin.ModelAdmin):
    """A basic admin panel to demonstrate normal storage behaviour"""


class ExampleBlobFieldModelAdmin(admin.ModelAdmin):
    """A basic admin panel to demonstrate the direct upload storage behaviour"""


class ExampleBlankBlobFieldModelAdmin(admin.ModelAdmin):
    """A basic admin panel to demonstrate the direct upload storage behaviour where blank=True"""


class ExampleUneditableBlobFieldModelAdmin(admin.ModelAdmin):
    """A basic admin panel to demonstrate the direct upload storage behaviour where blank=True"""


class ExampleMultipleBlobFieldModelAdmin(admin.ModelAdmin):
    """A basic admin panel to demonstrate the direct upload storage behaviour where multiple blobfields are used"""


admin.site.register(ExampleStorageModel, ExampleStorageModelAdmin)
admin.site.register(ExampleBlobFieldModel, ExampleBlobFieldModelAdmin)
admin.site.register(ExampleBlankBlobFieldModel, ExampleBlankBlobFieldModelAdmin)
admin.site.register(ExampleUneditableBlobFieldModel, ExampleUneditableBlobFieldModelAdmin)
admin.site.register(ExampleMultipleBlobFieldModel, ExampleMultipleBlobFieldModelAdmin)
