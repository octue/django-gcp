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
from django_gcp.exceptions import DuplicateTaskError, IncorrectTaskUsageError
from django_gcp.tasks import OnDemandTask
from gcp_pilot.mocker import patch_auth
from google.api_core.exceptions import AlreadyExists

from tests.server.example.tasks import DeduplicatedOnDemandTask, MyOnDemandTask
from .test_events_utils import DEFAULT_SUBSCRIPTION


class TasksEnqueueingTest(SimpleTestCase):
    def test_instantiate_task_directly(self):
        with self.assertRaises(IncorrectTaskUsageError):
            OnDemandTask()

    def test_enqueue_duplicatable_on_demand_task(self):

        with patch_auth():
            with patch("gcp_pilot.tasks.CloudTasks.push"):
                MyOnDemandTask().enqueue(a="1")

    def test_enqueue_deduplicated_task_raises_exception_on_duplicate(self):
        """Ensures that a unique task cannot be enqueued"""

        with patch_auth():
            with patch("gcp_pilot.tasks.CloudTasks.push") as patched_push:
                patched_push.side_effect = AlreadyExists("409 Requested entity already exists")

                with self.assertRaises(DuplicateTaskError):
                    DeduplicatedOnDemandTask().enqueue(a="1")

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

    def test_failing_on_demand_task_returns_error(self):
        url = reverse("gcp-tasks", args=["FailingOnDemandTask"])
        data = {"a": 1}
        response = self.client.post(path=url, data=json.dumps(data), content_type="application/json")

        self.assertEqual(500, response.status_code)
        self.assertIn("error", response.json())
