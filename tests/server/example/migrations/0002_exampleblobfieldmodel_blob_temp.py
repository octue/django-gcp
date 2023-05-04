import django_gcp.storage.fields
from django.db import migrations
from django.test import override_settings

import tests.server.example.models


def copy_to_blob_temp(apps, _):
    """Copy data from FileField to a temporary BlobField"""

    # Allowing the client to set paths directly is insecure, as it could allow a malicious
    # actor to assume permissions to access an object given its path. But, sometimes we need
    # to set the path directly ourselves. To do that we set this escape hatch (should always
    # be set to False in production)
    with override_settings(GCP_STORAGE_OVERRIDE_BLOBFIELD_VALUE=True):
        Model = apps.get_model("example", "ExampleBlobFieldModel")

        for instance in Model.objects.all():
            as_file = instance.blob
            instance.blob_temp = {"path": str(as_file.name)}
            instance.save()
            # NOTE: You could choose to execute the naming callback and move the blobs
            # to consistent locations here if you want to. However, that involves a
            # lot of interactions with the Google API, making this migration very slow
            # and subject to failure so we'd recommend doing that as a separate job in a
            # management command.


def copy_to_blob_temp_reverse(apps, _):
    """Reverts change"""
    Model = apps.get_model("example", "ExampleBlobFieldModel")

    for instance in Model.objects.all():
        value_or_dict = instance.blob_temp or {}
        instance.blob = value_or_dict.get("path", None)
        instance.save()


class Migration(migrations.Migration):
    """Adds a temporary field, then copies the existing data from the filefield to that.

    See subsequent migrations too for the complete set.
    """

    dependencies = [
        ("example", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="exampleblobfieldmodel",
            name="blob_temp",
            field=django_gcp.storage.fields.BlobField(
                default=dict,
                get_destination_path=tests.server.example.models.get_destination_path,
                help_text="GCP cloud storage object",
                ingress_to="_tmp/",
                store_key="media",
            ),
        ),
        migrations.RunPython(copy_to_blob_temp, copy_to_blob_temp_reverse),
        # This is what we do next.
        # But, do not attempt to do the following in a single migration... these
        # operations should be done in separate migrations for databases like postgres
        #  (see https://stackoverflow.com/questions/38023545/is-it-safe-to-do-a-data-migration-as-just-one-operation-in-a-larger-django-migra)
        # migrations.RemoveField(
        #     model_name="exampleblobfieldmodel",
        #     name="blob",
        # ),
        # migrations.RenameField(
        #     model_name="exampleblobfieldmodel",
        #     old_name="blob_temp",
        #     new_name="blob",
        # ),
    ]
