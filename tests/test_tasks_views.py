# Disables for testing:
# pylint: disable=missing-docstring
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods

# Disabled because gcloud api dynamically constructed
# pylint: disable=no-member

import json
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import reverse

from django_gcp.events.utils import make_pubsub_message
from django_gcp.tasks.views import GoogleCloudTaskView

from ._utils import authenticated_oidc_caller, patch_auth
from .test_events_utils import DEFAULT_SUBSCRIPTION

INVOKER_EMAIL = "invoker@test-project.iam.gserviceaccount.com"


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


@override_settings(GCP_TASKS_DISABLE_AUTH=True)
class TasksViewTest(SimpleTestCase):
    """Tests of the task execution mechanics, with endpoint authentication disabled."""

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


@override_settings(GCP_TASKS_DISABLE_AUTH=True)
class TasksViewNotFoundTest(SimpleTestCase):
    """The unknown-task 404 must not leak the available task names except in DEBUG mode."""

    def _post_unknown_task(self):
        url = reverse("gcp-tasks", args=["NotAValidTaskName"])
        return self.client.post(path=url, data=json.dumps({"a": 1}), content_type="application/json")

    def test_unknown_task_404_omits_available_tasks(self):
        response = self._post_unknown_task()

        self.assertEqual(404, response.status_code)
        self.assertIn("error", response.json())
        self.assertNotIn("available_tasks", response.json())

    @override_settings(DEBUG=True)
    def test_unknown_task_404_includes_available_tasks_in_debug_mode(self):
        response = self._post_unknown_task()

        self.assertEqual(404, response.status_code)
        self.assertIn("error", response.json())
        self.assertIn("available_tasks", response.json())


class TasksViewAuthTest(SimpleTestCase):
    """Tests of OIDC authentication on the task endpoints."""

    def _claims(self, email=INVOKER_EMAIL, url=None):
        claims = {"email": email, "email_verified": True}
        if url is not None:
            claims["aud"] = f"http://testserver{url}"
        return claims

    def _post_on_demand_task(self, **extra):
        url = reverse("gcp-tasks", args=["MyOnDemandTask"])
        return self.client.post(path=url, data=json.dumps({"a": 1}), content_type="application/json", **extra)

    def test_anonymous_post_to_task_endpoint_is_401(self):
        response = self._post_on_demand_task()

        self.assertEqual(401, response.status_code)

    def test_anonymous_post_to_subscriber_task_endpoint_is_401(self):
        url = reverse("gcp-subscriber-tasks", args=["MySubscriberTask"])
        msg = make_pubsub_message({"a": 1}, DEFAULT_SUBSCRIPTION)
        response = self.client.post(path=url, data=msg, content_type="application/json")

        self.assertEqual(401, response.status_code)

    def test_authenticated_caller_runs_the_task(self):
        with patch("tests.server.example.tasks.MyOnDemandTask.run", return_value={"b": 2}) as patched_run:
            with authenticated_oidc_caller():
                response = self._post_on_demand_task()

        self.assertEqual(200, response.status_code)
        self.assertEqual({"result": {"b": 2}}, response.json())
        patched_run.assert_called_once_with(a=1)

    @override_settings(GCP_TASKS_INVOKER_SERVICE_ACCOUNT_EMAILS=[INVOKER_EMAIL])
    def test_caller_in_tasks_invoker_setting_is_accepted(self):
        url = reverse("gcp-tasks", args=["MyOnDemandTask"])
        with patch("tests.server.example.tasks.MyOnDemandTask.run", return_value=None) as patched_run:
            with patch(
                "django_gcp.auth.oidc.id_token.verify_oauth2_token",
                return_value=self._claims(url=url),
            ):
                response = self._post_on_demand_task(HTTP_AUTHORIZATION="Bearer a-token")

        self.assertEqual(200, response.status_code)
        patched_run.assert_called_once_with(a=1)

    @override_settings(GCP_INVOKER_SERVICE_ACCOUNT_EMAILS=[INVOKER_EMAIL])
    def test_caller_in_shared_invoker_setting_is_accepted(self):
        url = reverse("gcp-tasks", args=["MyOnDemandTask"])
        with patch("tests.server.example.tasks.MyOnDemandTask.run", return_value=None) as patched_run:
            with patch(
                "django_gcp.auth.oidc.id_token.verify_oauth2_token",
                return_value=self._claims(url=url),
            ):
                response = self._post_on_demand_task(HTTP_AUTHORIZATION="Bearer a-token")

        self.assertEqual(200, response.status_code)
        patched_run.assert_called_once_with(a=1)

    @override_settings(GCP_TASKS_INVOKER_SERVICE_ACCOUNT_EMAILS=[INVOKER_EMAIL])
    def test_unlisted_caller_is_403(self):
        url = reverse("gcp-tasks", args=["MyOnDemandTask"])
        with patch(
            "django_gcp.auth.oidc.id_token.verify_oauth2_token",
            return_value=self._claims(email="someone-else@test-project.iam.gserviceaccount.com", url=url),
        ):
            response = self._post_on_demand_task(HTTP_AUTHORIZATION="Bearer a-token")

        self.assertEqual(403, response.status_code)

    def test_view_with_auth_required_false_executes_anonymously(self):
        url = reverse("gcp-tasks", args=["MyOnDemandTask"])
        request = RequestFactory().post(url, data=json.dumps({"a": 1}), content_type="application/json")
        view = GoogleCloudTaskView.as_view(auth_required=False)

        with patch("tests.server.example.tasks.MyOnDemandTask.run", return_value={"b": 2}) as patched_run:
            response = view(request, task_name="MyOnDemandTask")

        self.assertEqual(200, response.status_code)
        patched_run.assert_called_once_with(a=1)

    def test_view_with_explicit_allowed_list_accepts_caller_without_settings(self):
        url = reverse("gcp-tasks", args=["MyOnDemandTask"])
        request = RequestFactory().post(
            url,
            data=json.dumps({"a": 1}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer a-token",
        )
        view = GoogleCloudTaskView.as_view(allowed_service_account_emails=[INVOKER_EMAIL])

        with patch("tests.server.example.tasks.MyOnDemandTask.run", return_value={"b": 2}) as patched_run:
            with patch(
                "django_gcp.auth.oidc.id_token.verify_oauth2_token",
                return_value=self._claims(url=url),
            ):
                response = view(request, task_name="MyOnDemandTask")

        self.assertEqual(200, response.status_code)
        patched_run.assert_called_once_with(a=1)
