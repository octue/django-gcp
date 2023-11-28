import json
from django.conf import settings
from django.forms import Widget


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
        ingress_path=None,
        accept_mimetype=DEFAULT_ACCEPT_MIMETYPE,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._args = args
        self._kwargs = kwargs
        self.accept_mimetype = accept_mimetype
        self.signed_ingress_url = signed_ingress_url
        self.ingress_path = ingress_path

        if "unfold" in settings.INSTALLED_APPS:
            self.template_name = "django_gcp/contrib/unfold/cloud_object_widget.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)

        # if self.is_initial():
        #     context["my_context"] = "Adding a new model"
        # else:
        #     context["my_context"] = "Changing an existing model"

        context["signed_ingress_url"] = self.signed_ingress_url
        context["ingress_path"] = self.ingress_path
        context["accept_mimetype"] = self.accept_mimetype
        # Yes I know this is a hack but I've been working on this for weeks and django's a nightmare
        value_or_dict = json.loads(value) or {}
        context["existing_path"] = value_or_dict.get("path", "")
        # context["signing_token"] = a token
        # context["signing_url"] = submit the token to this url in exchange for a signed URL reverse("gcp-storage-get-direct-upload-url")
        return context
