# Disables for testing:
# pylint: disable=missing-docstring

import json

from django.db import connection
from django_test_migrations.contrib.unittest_case import MigratorTestCase


class FileToBlobMigrationTestCase(MigratorTestCase):
    """This class is used to test a migration that alters a FileField to a BlobField"""

    migrate_from = ("example", "0001_initial")
    migrate_to = ("example", "0004_rename_blob_temp_exampleblobfieldmodel_blob")

    def prepare(self):
        """Prepare original data at migration 0001, containing the
        string filename for a populated FileField.

        Note that these need to be done with custom SQL entries,
        because models may no longer exist as the repo evolves.

        These statements were generated with the example model and code
        at migration 0001 then using DJANGO DEBUG TOOLBAR with the
        intercept_redirects field set to True, to record the POST
        request for making a model.

        You can also do it programatically
        ```py
            from django.db import connection
            print(connection.queries)
        ```
        shows the sql you executed within the shell context, which gets replicated here
        """

        with connection.cursor() as cursor:
            cursor.execute(
                'INSERT INTO "example_exampleblobfieldmodel" ("blob") VALUES (\'test/file_to_blob_migration.txt\') RETURNING "example_exampleblobfieldmodel"."id"'
            )

    def test_migration_from_file_field(self):
        """Ensure that the string left over"""

        # Ensure an example entry was created
        ExampleBlobFieldModel = self.new_state.apps.get_model("example", "ExampleBlobFieldModel")
        self.assertEqual(ExampleBlobFieldModel.objects.count(), 1)

        # The new model should contain a json string
        row = ExampleBlobFieldModel.objects.first()
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT "blob" FROM "example_exampleblobfieldmodel" WHERE "id" = {row.id}')
            # The first (only) row should contain a decodable json string
            result = json.loads(cursor.fetchone()[0])

        self.assertEqual(result["path"], "test/file_to_blob_migration.txt")
