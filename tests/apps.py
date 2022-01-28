from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RabidArmadilloTestAppConfig(AppConfig):
    name = 'tests'
    label = 'tests'
    verbose_name = _('Rabid Armadillo Test App')
