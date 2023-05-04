from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("example", "0003_remove_exampleblobfieldmodel_blob"),
    ]

    operations = [
        migrations.RenameField(
            model_name="exampleblobfieldmodel",
            old_name="blob_temp",
            new_name="blob",
        ),
    ]
