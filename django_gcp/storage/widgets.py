import json

from django.conf import settings
from django.forms import Widget

from .operations import UNLIMITED_MAX_SIZE

DEFAULT_ACCEPT_MIMETYPE = "*/*"


class CloudObjectWidget(Widget):
    """A widget allowing upload of a file directly to cloud storage

    Must be placed in a form context. On submission of the form,
    upload is started. The submission is intercepted and re-triggered
    on completion of the upload.
    """

    class Media:
        """Add css and js assets to the template rendering the widget"""

        css = {
            "all": ["django_gcp/cloud_object_widget.css"],
        }
        js = ["django_gcp/cloud_object_widget.js"]

    template_name = "django_gcp/cloud_object_widget.html"

    def __init__(
        self,
        *args,
        signed_ingress_url=None,
        max_size_bytes=UNLIMITED_MAX_SIZE,
        ingress_path=None,
        accept_mimetype=DEFAULT_ACCEPT_MIMETYPE,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._args = args
        self._kwargs = kwargs
        self.accept_mimetype = accept_mimetype
        self.signed_ingress_url = signed_ingress_url
        self.max_size_bytes = max_size_bytes
        self.ingress_path = ingress_path

        if "unfold" in settings.INSTALLED_APPS:
            self.template_name = "django_gcp/contrib/unfold/cloud_object_widget.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["max_size_bytes"] = self.max_size_bytes
        context["signed_ingress_url"] = self.signed_ingress_url
        context["ingress_path"] = self.ingress_path
        context["accept_mimetype"] = self.accept_mimetype

        # Attach these to the instantiated widget in the ModelForm if you
        # want download and console buttons to appear
        if hasattr(self, "console_url"):
            context["console_url"] = self.console_url

        if hasattr(self, "download_url"):
            context["download_url"] = self.download_url

        # Yes I know this is a hack but I've been working on this for weeks and django's a nightmare
        value_or_dict = json.loads(value) or {}
        context["existing_path"] = value_or_dict.get("path", "")
        return context
