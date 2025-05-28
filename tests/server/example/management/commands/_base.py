import abc

from django.apps import apps
from django.core.management.base import BaseCommand as DjangoBaseCommand


class BaseCommand(DjangoBaseCommand, abc.ABC):
    """A BaseCommand with additional helpers for task-related management commands"""

    @property
    def task_manager(self):
        """Return the task manager via the app configuration"""
        return apps.get_app_config("django_gcp").task_manager

    def display_task_report(self, report, action, name):
        """Print a report to stdout on the task successes"""

        n = len(report)
        report_str = "\n".join([f"- {name}" for name in report])

        message = f"Successfully {action}d {n} {name} to domain {self.task_manager.domain}\n{report_str}"
        self.stdout.write(self.style.SUCCESS(message))  # pylint: disable=no-member
