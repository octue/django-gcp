# Disables for testing:
# pylint: disable=missing-docstring
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods

from io import StringIO
from typing import List
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from django_gcp.exceptions import UnknownActionError
from django_gcp.tasks._pilot.mocker import patch_auth


class CommandsTest(SimpleTestCase):
    def patch_schedule(self, **kwargs):
        return patch("django_gcp.tasks._pilot.scheduler.CloudScheduler.put", **kwargs)

    def patch_subscribe(self, **kwargs):
        return patch("django_gcp.tasks._pilot.pubsub.CloudSubscriber.create_subscription", **kwargs)

    def patch_get_scheduled(self, names: List[str] = None, **kwargs):
        jobs = []
        for name in names or []:
            job = Mock()
            job.name = f"/app/jobs/{name}"
            jobs.append(job)
        return patch("django_gcp.tasks._pilot.scheduler.CloudScheduler.list", return_value=jobs, **kwargs)

    def patch_delete_schedule(self):
        return patch("django_gcp.tasks._pilot.scheduler.CloudScheduler.delete")

    def _assert_command(
        self,
        command: str,
        params: List[str] = None,
        expected_schedule_calls: int = 0,
        expected_subscribe_calls: int = 0,
        expected_get_scheduled_calls: int = 0,
        expected_output: str = None,
        scheduled_job_names: List[str] = None,
    ):
        out = StringIO()
        with patch_auth():
            with self.patch_schedule() as schedule:
                with self.patch_subscribe() as subscribe:
                    scheduled_job_names = scheduled_job_names or []
                    with self.patch_get_scheduled(names=scheduled_job_names) as get_scheduled:
                        call_params = params or []
                        call_command(command, *call_params, no_color=True, stdout=out)

        self.assertEqual(expected_schedule_calls, schedule.call_count)
        self.assertEqual(expected_subscribe_calls, subscribe.call_count)
        self.assertEqual(expected_get_scheduled_calls, get_scheduled.call_count)
        if expected_output:
            self.assertEqual(expected_output, out.getvalue())

        return out.getvalue()

    def test_unknown_manager_action(self):
        out = StringIO()
        with self.assertRaises(UnknownActionError):
            call_command("task_manager", "someActionThatDoesntExist", no_color=True, stdout=out)

    def test_create_scheduler_jobs(self):
        with override_settings(GCP_TASKS_DOMAIN="https://wherever.com"):
            out = self._assert_command(
                command="task_manager",
                params=["create_scheduler_jobs"],
                expected_schedule_calls=1,
                expected_get_scheduled_calls=0,
            )
        self.assertIn(
            "Successfully created 1 scheduler jobs to domain https://wherever.com",
            out,
        )
        self.assertIn(
            "- [+] django-gcp--myperiodictask",
            out,
        )

    def test_create_scheduler_jobs_with_no_cleanup_affix(self):
        with override_settings(GCP_TASKS_RESOURCE_AFFIX=None):
            with override_settings(GCP_TASKS_DOMAIN="https://wherever.com"):
                self._assert_command(
                    command="task_manager",
                    params=["create_scheduler_jobs", "--cleanup"],
                    expected_schedule_calls=1,
                    expected_get_scheduled_calls=0,
                )
        # TODO ensure that the right warning appears in logs
        # self.assertIn(
        #     "Cleanup of unused Scheduler Jobs was requested but skipped, because no resource affix was given - see the GCP_TASKS_RESOURCE_AFFIX docs for more details.",
        #     out,
        # )

    def test_create_scheduler_jobs_with_cleanup_affix(self):
        with override_settings(GCP_TASKS_RESOURCE_AFFIX="notnone"):
            with override_settings(GCP_TASKS_DOMAIN="https://wherever.com"):
                self._assert_command(
                    command="task_manager",
                    params=["create_scheduler_jobs", "--cleanup"],
                    expected_schedule_calls=1,
                    expected_get_scheduled_calls=1,
                )
        # TODO mock the response from get_expected and assert that the deletion is called
        # It might look a bit like this:
        # from unittest.mock import patch, Mock, PropertyMock
        #     expected_output = (
        #         "Successfully scheduled 3 tasks to domain http://localhost:8080"
        #         "\n- [+] SaySomethingTask"
        #         "\n- [-] potato_task_1"
        #         "\n- [-] potato_task_2\n"
        #     )
        #     names = ["potato_task_1", "potato_task_2"]
        #     app_config = apps.get_app_config("django_cloud_tasks")
        #     with patch.object(app_config, "app_name", new_callable=PropertyMock, return_value="potato"):
        #         with self.patch_get_scheduled(names=names):
        #             with self.patch_delete_schedule() as delete:
        #                 self._assert_command(
        #                     command="schedule_tasks",
        #                     expected_schedule_calls=1,
        #                     expected_output=expected_output,
        #                 )
        #             self.assertEqual(2, delete.call_count)

    def test_create_pubsub_subscriptions(self):
        with override_settings(GCP_TASKS_DOMAIN="https://wherever.com"):
            out = self._assert_command(
                command="task_manager",
                params=["create_pubsub_subscriptions"],
                expected_subscribe_calls=1,
                expected_schedule_calls=0,
                expected_get_scheduled_calls=0,
            )
        self.assertEqual(
            "Successfully created 1 pubsub subscriptions to domain https://wherever.com\n- [+] MySubscriberTask\n",
            out,
        )
