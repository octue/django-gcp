from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

from django_gcp.storage import GoogleCloudStorage


# pylint: disable=missing-class-docstring
class Command(BaseCommand):
    help = "Cleanup temporary files in Google Cloud Storage. When ingressing files to temporary blobs, any failure to save the corresponding model will result in an orphaned upload."

    def add_arguments(self, parser):
        parser.add_argument("store_key", type=str, help="Google Cloud Storage key")
        parser.add_argument("--delete", action="store_true", help="Delete the temporary files")

    def handle(self, *args, **options):
        store_key = options["store_key"]
        delete_files = options["delete"]

        # Instantiate GoogleCloudStorage
        store = GoogleCloudStorage(store_key=store_key)
        bucket = store.bucket

        # Filter blobs with name starting with '_tmp' and age over 24 hours
        blob_list = bucket.list_blobs(prefix="_tmp")
        tmp_files = []
        for blob in blob_list:
            age = datetime.now() - blob.time_created.replace(tzinfo=None)
            if age > timedelta(hours=24):
                tmp_files.append(blob)

        # Print the list of temporary files
        if tmp_files:
            print(f"Temporary files to delete: {[blob.name for blob in tmp_files]}")
        else:
            print("No temporary files to delete")

        # Delete the temporary files if the --delete flag was passed
        if delete_files and tmp_files:
            bucket.delete_blobs(tmp_files)
            print(f"Deleted {len(tmp_files)} temporary files")
