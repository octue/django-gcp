"""In-app OIDC verification for Django endpoints called by GCP services.

Cloud Tasks, Cloud Scheduler, Pub/Sub push subscriptions and Cloud Workflows all attach a Google
OIDC identity token to the HTTP calls they make. Platform IAM may already gate the intended route
(for example an internal-ingress Cloud Run service), but when the same application is also served
publicly the token must be verified in-app: valid signature, audience matching this request's
URI, and a verified email in an allowed service account list.
"""

from functools import wraps
import logging

from django.conf import settings
from django.http import JsonResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

logger = logging.getLogger(__name__)

SHARED_INVOKER_EMAILS_SETTING = "GCP_INVOKER_SERVICE_ACCOUNT_EMAILS"


def verify_oidc_token(request, allowed_service_account_emails=None, settings_names=(SHARED_INVOKER_EMAILS_SETTING,)):
    """Verify that a request carries a valid GCP OIDC identity token from an allowed service account.

    The token must have a valid signature, an audience equal to this request's absolute URI (with
    or without its query string, because Pub/Sub push tokens default to the full push URL while
    tokens attached by django-gcp use the URL without a query string), and a verified email in the
    allowed service account list.

    :param request: the Django request to verify
    :param allowed_service_account_emails: iterable of caller emails to accept; when None, the
        allow-list is read from the first name in ``settings_names`` that exists as a Django
        setting, defaulting to empty (which rejects every caller)
    :param settings_names: ordered names of Django settings to consult for the allow-list
    :return: a ``(claims, error)`` tuple — ``(claims, None)`` on success, or ``(None, JsonResponse)``
        carrying the 401/403 to return
    """
    if allowed_service_account_emails is None:
        allowed_service_account_emails = []
        for settings_name in settings_names:
            if hasattr(settings, settings_name):
                allowed_service_account_emails = getattr(settings, settings_name)
                break

    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None, JsonResponse({"error": "Missing bearer token"}, status=401)

    token = authorization.removeprefix("Bearer ")
    audience = [request.build_absolute_uri(request.path), request.build_absolute_uri()]

    try:
        claims = id_token.verify_oauth2_token(token, google_requests.Request(), audience=audience)
    except ValueError as e:
        logger.warning("Rejected OIDC token: %s", e)
        return None, JsonResponse({"error": "Invalid token"}, status=401)

    if not claims.get("email_verified") or claims.get("email") not in allowed_service_account_emails:
        logger.warning("Rejected OIDC token for email %s", claims.get("email"))
        return None, JsonResponse({"error": "Forbidden"}, status=403)

    return claims, None


def oidc_required(view_func=None, allowed_service_account_emails=None, settings_names=(SHARED_INVOKER_EMAILS_SETTING,)):
    """Decorate a view to require a valid GCP OIDC identity token.

    On success the verified claims are attached to the request as ``request.oidc_claims`` and the
    view runs; on failure the 401/403 ``JsonResponse`` is returned without calling the view.

    Usable bare or with arguments::

        @oidc_required
        def my_view(request): ...

        @oidc_required(allowed_service_account_emails=["invoker@my-project.iam.gserviceaccount.com"])
        def my_view(request): ...

        @oidc_required(settings_names=("GCP_WORKFLOWS_INVOKER_SERVICE_ACCOUNT_EMAILS", "GCP_INVOKER_SERVICE_ACCOUNT_EMAILS"))
        def my_workflow_callback(request): ...

    :param view_func: the view being decorated when used without arguments
    :param allowed_service_account_emails: iterable of caller emails to accept; when None, the
        allow-list is resolved from ``settings_names``
    :param settings_names: ordered names of Django settings to consult for the allow-list
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            claims, error = verify_oidc_token(request, allowed_service_account_emails, settings_names=settings_names)
            if error is not None:
                return error
            request.oidc_claims = claims
            return func(request, *args, **kwargs)

        return wrapper

    if view_func is not None:
        return decorator(view_func)
    return decorator


class OIDCAuthRequiredMixin:
    """Require a valid GCP OIDC identity token before dispatching a class-based view.

    Verification runs before HTTP method routing, so unauthenticated requests receive 401/403
    regardless of method. On success the verified claims are attached as ``request.oidc_claims``.

    The class attributes are accepted as ``as_view()`` keyword arguments, allowing per-URL
    overrides when wiring the view manually::

        GoogleCloudEventsView.as_view(auth_required=False)
        GoogleCloudTaskView.as_view(allowed_service_account_emails=["invoker@my-project.iam.gserviceaccount.com"])
    """

    auth_required = True
    allowed_service_account_emails = None
    invoker_emails_settings = (SHARED_INVOKER_EMAILS_SETTING,)
    disable_auth_setting = None

    def dispatch(self, request, *args, **kwargs):
        if self._auth_enabled():
            claims, error = verify_oidc_token(
                request,
                self.allowed_service_account_emails,
                settings_names=self.invoker_emails_settings,
            )
            if error is not None:
                return error
            request.oidc_claims = claims
        return super().dispatch(request, *args, **kwargs)

    def _auth_enabled(self):
        # The disable setting is read per-request (not cached) so `override_settings` works in
        # tests and settings changes do not require re-wiring urlconfs
        if not self.auth_required:
            return False
        if self.disable_auth_setting is not None and getattr(settings, self.disable_auth_setting, False):
            return False
        return True
