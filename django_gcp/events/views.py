import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from django_gcp.auth import OIDCAuthRequiredMixin

from .signals import event_received

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class GoogleCloudEventsView(OIDCAuthRequiredMixin, View):
    """Handles events inbound from Google Cloud services like Pub/Sub by dispatch to a django signal

    Callers must present a valid OIDC identity token from a service account listed in
    ``GCP_EVENTS_INVOKER_SERVICE_ACCOUNT_EMAILS`` (falling back to
    ``GCP_INVOKER_SERVICE_ACCOUNT_EMAILS``), unless ``GCP_EVENTS_DISABLE_AUTH`` is True or the
    view is wired with ``as_view(auth_required=False)``.

    Any exceptions thrown by the handlers will be returned to the client as 400s.

    """

    invoker_emails_settings = ("GCP_EVENTS_INVOKER_SERVICE_ACCOUNT_EMAILS", "GCP_INVOKER_SERVICE_ACCOUNT_EMAILS")
    disable_auth_setting = "GCP_EVENTS_DISABLE_AUTH"

    def post(self, request, event_kind, event_reference):
        """Handle a POSTed event"""
        try:
            event_payload = json.loads(request.body)
            event_parameters = request.GET.dict()
            event_received.send(
                sender=self.__class__,
                event_kind=event_kind,
                event_reference=event_reference,
                event_payload=event_payload,
                event_parameters=event_parameters,
            )
            return self._prepare_response(status=201, payload={})

        except Exception as e:  # pylint: disable=broad-except
            if getattr(settings, "DEBUG", False):
                raise e
            else:
                msg = f"Unable to handle event of kind {event_kind} with reference {event_reference}"
                logger.warning("%s. Exception: %s", msg, str(e))
                return self._prepare_response(status=400, payload={"error": msg})

    def _prepare_response(self, status, payload):
        return HttpResponse(status=status, content=json.dumps(payload), content_type="application/json")
