from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RabidArmadilloAppConfig(AppConfig):
    name = 'rabid_armadillo'
    label = 'rabid_armadillo'
    verbose_name = _('Rabid Armadillo')

    def ready(self):
        from rabid_armadillo.signals import register_signal_handlers
        register_signal_handlers()
