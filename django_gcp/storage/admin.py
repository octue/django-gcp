from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from .blob_utils import (
    get_console_url,
    get_path,
    get_signed_download_url,
)
from .fields import BlobField


class BlobFieldModelAdminMixin:
    def get_readonly_blob_widget(self, obj, field_name):
        context = {
            "existing_path": get_path(obj, field_name),
            "download_url": get_signed_download_url(obj, field_name),
            "console_url": get_console_url(obj, field_name),
        }
        return mark_safe(render_to_string("django_gcp/contrib/unfold/cloud_object_readonly_widget.html", context))

    def _replace_blob_field_names(self, fields, fields_to_replace):
        blob_fields = set(f.name for f in self.model._meta.get_fields() if isinstance(f, BlobField))

        # suffix field names with __readonly if they're blob fields
        for i, item in enumerate(fields):
            if item in fields_to_replace:
                fields[i] = f"{item}__readonly"

                # Check that the appropriate setup is done
                if item not in blob_fields:
                    raise ValueError(
                        f"The field {item} is not a BlobField, but is in readonly_blob_fields. "
                        f"Please remove it from readonly_blob_fields."
                    )
        return fields

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)

        # Regardless of whether adding or editing, any read_only_blob_fields
        # need to be switched for custom defined fields
        if hasattr(self, "read_only_blob_fields"):
            fields = self._replace_blob_field_names(fields, self.read_only_blob_fields)

        if obj is not None and hasattr(self, "create_only_blob_fields"):
            # When adding a new object, create_only_blob_fields should be left alone
            # because they need to be set on object creation. When editing an existing
            # object, however, we ALSO pull the switcharoo create_only_blob_fields
            fields = self._replace_blob_field_names(fields, self.create_only_blob_fields)

        return fields

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if hasattr(self, "read_only_blob_fields"):
            readonly_fields = [*readonly_fields, *self.read_only_blob_fields]
            readonly_fields = self._replace_blob_field_names(readonly_fields, self.read_only_blob_fields)

        if obj is not None and hasattr(self, "create_only_blob_fields"):
            readonly_fields = [*readonly_fields, *self.create_only_blob_fields]
            readonly_fields = self._replace_blob_field_names(readonly_fields, self.create_only_blob_fields)

        return readonly_fields
