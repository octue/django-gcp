# Disables for testing:
# pylint: disable=missing-docstring
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods

# Disabled because gcloud api dynamically constructed
# pylint: disable=no-member

import json
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from google.api_core.exceptions import AlreadyExists

from django_gcp.events.utils import make_pubsub_message
from django_gcp.exceptions import DuplicateTaskError, IncompatibleSettingsError, IncorrectTaskUsageError
from django_gcp.tasks import OnDemandTask
from django_gcp.tasks._pilot.mocker import patch_auth
from tests.server.example.tasks import (
    DeduplicatedOnDemandTask,
    FailingOnDemandTask,
    MyOnDemandTask,
    MyPeriodicTask,
    MySubscriberTask,
)

from .test_events_utils import DEFAULT_SUBSCRIPTION


class TasksEnqueueingTest(SimpleTestCase):
    def test_instantiate_task_directly(self):
        with self.assertRaises(IncorrectTaskUsageError):
            OnDemandTask()

    def test_enqueue_duplicatable_on_demand_task(self):
        with patch_auth():
            with patch("django_gcp.tasks._pilot.tasks.CloudTasks.push"):
                MyOnDemandTask().enqueue(a="1")

    def test_enqueue_deduplicated_task_raises_exception_on_duplicate(self):
        """Ensures that a unique task cannot be enqueued"""

        with patch_auth():
            with patch("django_gcp.tasks._pilot.tasks.CloudTasks.push") as patched_push:
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

    def test_disable_enqueueing_with_a_setting(self):
        """Assert that no task is enqueued if the GCP_TASKS_DISABLE_EXECUTE is true"""
        with patch_auth():
            with patch("django_gcp.tasks.tasks.run_coroutine") as patched_send:
                MyOnDemandTask().enqueue(a="1")
                self.assertEqual(patched_send.call_count, 1)

                with override_settings(GCP_TASKS_DISABLE_EXECUTE=True):
                    MyOnDemandTask().enqueue(a="1")
                    MyPeriodicTask().enqueue(a="1")
                    MySubscriberTask().enqueue(a="1")
                    FailingOnDemandTask().enqueue(a="1")

                    self.assertEqual(patched_send.call_count, 1)

                    MyOnDemandTask().enqueue_later(a="1", when=10)
                    MyPeriodicTask().enqueue_later(a="1", when=10)
                    MySubscriberTask().enqueue_later(a="1", when=10)
                    FailingOnDemandTask().enqueue_later(a="1", when=10)

                    self.assertEqual(patched_send.call_count, 1)

            with override_settings(GCP_TASKS_DISABLE_EXECUTE=True, GCP_TASKS_EAGER_EXECUTE=True):
                with self.assertRaises(IncompatibleSettingsError):
                    MyOnDemandTask().enqueue(a="1")
