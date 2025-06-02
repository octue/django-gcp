import logging

from django.forms.fields import JSONField

from .widgets import CloudObjectWidget

logger = logging.getLogger(__name__)


class CloudObjectFormField(JSONField):
    """Overrides the forms.JSONField with a widget to handle file selection and upload"""

    empty_value = None
    widget = CloudObjectWidget
