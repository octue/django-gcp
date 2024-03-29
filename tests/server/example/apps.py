from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ExampleAppConfig(AppConfig):
    """Example (test server) app showing how you would use django-gcp within your own django server"""

    name = "tests.server.example"
    label = "example"
    verbose_name = _("Example App using Django GCP")

    def ready(self):
        # Import the tasks only once the app is ready, in order to register them
        from . import tasks  # noqa: F401, pylint: disable=unused-import, import-outside-toplevel
