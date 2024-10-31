from django.conf import settings
from django.test import override_settings

from django_gcp.exceptions import UnknownActionError

from ._base import BaseCommand


class Command(BaseCommand):
    """Use `python manage.py help create_resources` to display help for this command line administration tool"""

    help = "Allows creation of scheduler jobs and pubsub subscriptions via django-gcp"

    def add_arguments(self, parser):
        parser.add_argument(
            "actions",
            nargs="+",
            help="List of task manager actions to take. Valid actions include 'create_scheduler_jobs' and 'create_pubsub_subscriptions'",
        )

        parser.add_argument(
            "--cleanup",
            action="store_true",
            default=False,
            help="Clean up unused resources whose name is affixed with GCP_TASKS_RESOURCE_AFFIX",
        )

        parser.add_argument(
            "--tasks-domain",
            type=str,
            help="Optionally specify a domain to which the tasks will be sent. Overrides the default GCP_TASKS_DOMAIN value.",
        )

    def handle(self, actions, **options):
        cleanup = options["cleanup"]
        tasks_domain = options["tasks_domain"] or settings.GCP_TASKS_DOMAIN

        with override_settings(GCP_TASKS_DOMAIN=tasks_domain):
            for action in actions:
                if action == "create_scheduler_jobs":
                    updated, deleted = self.task_manager.create_scheduler_jobs(cleanup=cleanup)
                    report = [f"[+] {name}" for name in updated] + [f"[-] {name}" for name in deleted]
                    self.display_task_report(report, "create", "scheduler jobs")

                elif action == "create_pubsub_subscriptions":
                    updated, deleted = self.task_manager.create_pubsub_subscriptions(cleanup=cleanup)
                    report = [f"[+] {name}" for name in updated] + [f"[-] {name}" for name in deleted]
                    self.display_task_report(report, "create", "pubsub subscriptions")

                else:
                    raise UnknownActionError(
                        f"Unknown action {action}. Use `python manage.py task_manager --help` to see all options"
                    )
