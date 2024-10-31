# Disables for testing:
# pylint: disable=missing-docstring
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods

# Disabled because gcloud api dynamically constructed
# pylint: disable=no-member

import json
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from django_gcp.events.utils import make_pubsub_message
from django_gcp.tasks._pilot.mocker import patch_auth

from .test_events_utils import DEFAULT_SUBSCRIPTION


class ExampleAppViewTest(SimpleTestCase):
    def test_task_pushed_to_queue(self):
        url = reverse("enqueue-on-demand")

        with self.settings(GCP_TASKS_DOMAIN="https://the-domain.com"):
            with patch("django_gcp.tasks._pilot.tasks.CloudTasks.push") as patched_push:
                with patch_auth():
                    response = self.client.post(path=url, content_type="application/json")

            self.assertEqual(201, response.status_code)
            expected_call = dict(
                queue_name="example-primary",
                url="https://the-domain.com/example-django-gcp/tasks/MyOnDemandTask",
                payload='{"a": 1}',
            )
            patched_push.assert_called_once_with(**expected_call)


class TasksViewTest(SimpleTestCase):
    def test_on_demand_task_run_method_called_with_data(self):
        url = reverse("gcp-tasks", args=["MyOnDemandTask"])
        data = {"a": 1}
        patch_response = {"b": 2}
        with patch("tests.server.example.tasks.MyOnDemandTask.run", return_value=patch_response) as patched_run:
            response = self.client.post(path=url, data=json.dumps(data), content_type="application/json")

        self.assertEqual(200, response.status_code)
        self.assertEqual({"result": patch_response}, response.json())
        patched_run.assert_called_once_with(**data)

    def test_periodic_task_run_method_called_with_data(self):
        url = reverse("gcp-tasks", args=["MyPeriodicTask"])
        data = {"a": 1}
        patch_response = {"b": 2}
        with patch("tests.server.example.tasks.MyPeriodicTask.run", return_value=patch_response) as patched_run:
            response = self.client.post(path=url, data=json.dumps(data), content_type="application/json")

        self.assertEqual(200, response.status_code)
        self.assertEqual({"result": patch_response}, response.json())
        patched_run.assert_called_once_with(**data)

    def test_invalid_task_name(self):
        url = reverse("gcp-tasks", args=["NotAValidTaskName"])
        data = {"a": 1}
        response = self.client.post(path=url, data=json.dumps(data), content_type="application/json")

        self.assertEqual(404, response.status_code)
        self.assertIn("error", response.json())
        self.assertEqual("Task NotAValidTaskName not found", response.json()["error"])

    def test_subscriber_task_run_method_called_with_data(self):
        url = reverse("gcp-subscriber-tasks", args=["MySubscriberTask"])

        msg = make_pubsub_message({"a": 1}, DEFAULT_SUBSCRIPTION)
        with patch("tests.server.example.tasks.MySubscriberTask.run", return_value=None) as patched_run:
            response = self.client.post(path=url, data=msg, content_type="application/json")

        self.assertEqual(200, response.status_code)
        self.assertEqual({"result": None}, response.json())
        patched_run.assert_called_once()

    @patch("django_gcp.logs.error_reporting.GoogleErrorReportingHandler.emit")
    def test_failing_on_demand_task_returns_error(self, patched_emit):
        url = reverse("gcp-tasks", args=["FailingOnDemandTask"])
        data = {"a": 1}
        response = self.client.post(path=url, data=json.dumps(data), content_type="application/json")

        self.assertEqual(500, response.status_code)
        self.assertIn("error", response.json())
        patched_emit.assert_called()
