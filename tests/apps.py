from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TestAppConfig(AppConfig):
    name = "tests"
    label = "tests"
    verbose_name = _("Django GCP Test App")
