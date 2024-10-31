from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("example", "0002_exampleblobfieldmodel_blob_temp"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="exampleblobfieldmodel",
            name="blob",
        ),
    ]
