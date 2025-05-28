# Disables for testing:
# pylint: disable=missing-docstring
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods

# Disabled because gcloud api dynamically constructed
# pylint: disable=no-member

from django.test import SimpleTestCase, override_settings

from django_gcp.tasks.tasks import apply_resource_affix


class TasksUtilsTest(SimpleTestCase):
    def test_resource_affix_and_delimiter(self):
        with override_settings(GCP_TASKS_RESOURCE_AFFIX="something", GCP_TASKS_DELIMITER="///"):
            prefixed = apply_resource_affix("value", suffix=False)
            suffixed = apply_resource_affix("value", suffix=True)
            self.assertEqual(prefixed, "something///value")
            self.assertEqual(suffixed, "value///something")

        with override_settings(GCP_TASKS_RESOURCE_AFFIX=None, GCP_TASKS_DELIMITER="///"):
            prefixed = apply_resource_affix("value", suffix=False)
            self.assertEqual(prefixed, "value")
