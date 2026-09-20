# Disables for testing:
# pylint: disable=missing-docstring
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods

# Disabled because gcloud api dynamically constructed
# pylint: disable=no-member

from datetime import timedelta
import json
from unittest.mock import patch

from django.apps import apps
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from django.utils.timezone import now
from google.api_core.exceptions import AlreadyExists

from django_gcp.events.utils import make_pubsub_message
from django_gcp.exceptions import DuplicateTaskError, IncompatibleSettingsError, IncorrectTaskUsageError
from django_gcp.tasks import OnDemandTask
from django_gcp.tasks.tasks import short_sha
from tests.server.example.tasks import (
    DeduplicatedOnDemandTask,
    FailingOnDemandTask,
    MyOnDemandTask,
    MyPeriodicTask,
    MySubscriberTask,
)

from ._utils import patch_auth
from .test_events_utils import DEFAULT_SUBSCRIPTION


@override_settings(GCP_TASKS_DISABLE_AUTH=True)
class TasksEnqueueingTest(SimpleTestCase):
    """Tests of task enqueueing and execution mechanics, with endpoint authentication disabled."""

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

    def test_enqueueing_with_eager_execute(self):
        """Assert that tasks are successfully executed if GCP_TASKS_EAGER_EXECUTE is true"""

        with patch("tests.server.example.tasks.MyOnDemandTask.run", return_value=None) as patched_run:
            with override_settings(GCP_TASKS_DISABLE_EXECUTE=False, GCP_TASKS_EAGER_EXECUTE=True):
                result = MyOnDemandTask().enqueue(a="1")

        self.assertIsNone(result)
        patched_run.assert_called_once()

    def test_enqueue_deduplicated_task_pushes_unique_task_name(self):
        """The pushed task name of a deduplicated task combines the payload sha (as a
        prefix, to keep task IDs binomially distributed for queue efficiency) with the
        task slug and the resource affix, with uniquification disabled so that a repeated
        payload is rejected by Cloud Tasks rather than renamed
        """
        with patch_auth():
            with patch("django_gcp.tasks._pilot.tasks.CloudTasks.push") as patched_push:
                DeduplicatedOnDemandTask().enqueue(a="1")

        # The expected name composes the GCP_TASKS_DELIMITER ("--") and
        # GCP_TASKS_RESOURCE_AFFIX ("django-gcp") values from the test server settings
        payload = json.dumps({"a": "1"})
        patched_push.assert_called_once_with(
            queue_name="example-primary",
            url="http://127.0.0.1:8000/example-django-gcp/tasks/DeduplicatedOnDemandTask",
            payload=payload,
            task_name=f"{short_sha(payload)}--deduplicatedondemandtask--django-gcp",
            unique=False,
        )

    def test_enqueue_later_with_seconds(self):
        with patch_auth():
            with patch("django_gcp.tasks._pilot.tasks.CloudTasks.push") as patched_push:
                MyOnDemandTask().enqueue_later(when=10, a="1")

        self.assertEqual(patched_push.call_args.kwargs["delay_in_seconds"], 10)

    def test_enqueue_later_with_timedelta(self):
        with patch_auth():
            with patch("django_gcp.tasks._pilot.tasks.CloudTasks.push") as patched_push:
                MyOnDemandTask().enqueue_later(when=timedelta(minutes=2), a="1")

        self.assertEqual(patched_push.call_args.kwargs["delay_in_seconds"], 120)

    def test_enqueue_later_with_datetime(self):
        with patch_auth():
            with patch("django_gcp.tasks._pilot.tasks.CloudTasks.push") as patched_push:
                MyOnDemandTask().enqueue_later(when=now() + timedelta(hours=1), a="1")

        delay_in_seconds = patched_push.call_args.kwargs["delay_in_seconds"]
        self.assertAlmostEqual(delay_in_seconds, 3600, delta=5)

    def test_enqueue_later_with_unsupported_type_raises(self):
        with self.assertRaises(ValueError):
            MyOnDemandTask().enqueue_later(when="tomorrow", a="1")


class TasksRegistrationTest(SimpleTestCase):
    """Tests that the task manager registers the example project's tasks by kind

    The exact-set assertions are deliberate canaries: registering a task class of the
    wrong kind, or leaking an abstract class into a registry, must fail these tests.
    Adding a task to the example project requires updating the corresponding set here.
    """

    def setUp(self):
        self.manager = apps.get_app_config("django_gcp").task_manager

    def test_registered_on_demand_tasks(self):
        self.assertEqual(
            set(self.manager.on_demand_tasks),
            {"MyOnDemandTask", "DeduplicatedOnDemandTask", "FailingOnDemandTask", "ProcessBlobTask"},
        )

    def test_registered_periodic_tasks(self):
        self.assertEqual(set(self.manager.periodic_tasks), {"MyPeriodicTask"})

    def test_registered_subscriber_tasks(self):
        self.assertEqual(set(self.manager.subscriber_tasks), {"MySubscriberTask"})

    def test_abstract_tasks_are_not_registered(self):
        """Abstract task classes are templates for concrete tasks and must not be
        registered (registration would create queues, schedules or subscriptions for them)
        """
        registered = {
            *self.manager.on_demand_tasks,
            *self.manager.periodic_tasks,
            *self.manager.subscriber_tasks,
        }
        self.assertNotIn("BaseAbstractTask", registered)
        self.assertNotIn("OnDemandTask", registered)
        self.assertNotIn("PeriodicTask", registered)
        self.assertNotIn("SubscriberTask", registered)
