# Signal handlers have to be imported on app ready state to avoid circular imports
# pylint: disable=import-outside-toplevel

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DjangoGCPAppConfig(AppConfig):
    """Django application metadata and config"""

    name = "django_gcp"
    label = "django_gcp"
    verbose_name = _("Django GCP")
    task_manager = None

    def ready(self):
        from django_gcp.signals import register_signal_handlers

        register_signal_handlers()

        from django_gcp.tasks import TaskManager

        self.task_manager = TaskManager()
