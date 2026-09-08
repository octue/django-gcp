"""In-app OIDC verification for Django endpoints called by GCP Cloud Workflows."""

from functools import wraps
import logging

from django.conf import settings
from django.http import JsonResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

logger = logging.getLogger(__name__)


def verify_workflow_oidc_token(request, allowed_service_account_emails=None):
    """Verify that a request carries a valid GCP OIDC identity token from an allowed service account.

    Cloud Workflows calls HTTP endpoints with ``auth: {type: OIDC, audience: <url>}``. Platform
    IAM may already gate the intended route (for example an internal-ingress Cloud Run service),
    but when the same application is also served publicly the token must be verified in-app:
    valid signature, audience matching this request's absolute URI, and a verified email in the
    allowed service account list.

    :param request: the Django request to verify
    :param allowed_service_account_emails: iterable of caller emails to accept; defaults to
        ``settings.GCP_WORKFLOWS_INVOKER_SERVICE_ACCOUNT_EMAILS`` (itself defaulting to empty,
        which rejects every caller)
    :return: a ``(claims, error)`` tuple — ``(claims, None)`` on success, or ``(None, JsonResponse)``
        carrying the 401/403 to return
    """
    if allowed_service_account_emails is None:
        allowed_service_account_emails = getattr(settings, "GCP_WORKFLOWS_INVOKER_SERVICE_ACCOUNT_EMAILS", [])

    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None, JsonResponse({"error": "Missing bearer token"}, status=401)

    token = authorization.removeprefix("Bearer ")
    audience = request.build_absolute_uri(request.path)

    try:
        claims = id_token.verify_oauth2_token(token, google_requests.Request(), audience=audience)
    except ValueError as e:
        logger.warning("Rejected workflow OIDC token: %s", e)
        return None, JsonResponse({"error": "Invalid token"}, status=401)

    if not claims.get("email_verified") or claims.get("email") not in allowed_service_account_emails:
        logger.warning("Rejected workflow OIDC token for email %s", claims.get("email"))
        return None, JsonResponse({"error": "Forbidden"}, status=403)

    return claims, None


def workflow_oidc_required(view_func=None, allowed_service_account_emails=None):
    """Decorate a view to require a valid workflow OIDC token.

    On success the verified claims are attached to the request as ``request.workflow_oidc_claims``
    and the view runs; on failure the 401/403 ``JsonResponse`` is returned without calling the view.

    Usable bare or with arguments::

        @workflow_oidc_required
        def my_view(request): ...

        @workflow_oidc_required(allowed_service_account_emails=["workflows@my-project.iam.gserviceaccount.com"])
        def my_view(request): ...

    :param view_func: the view being decorated when used without arguments
    :param allowed_service_account_emails: iterable of caller emails to accept; defaults to
        ``settings.GCP_WORKFLOWS_INVOKER_SERVICE_ACCOUNT_EMAILS``
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            claims, error = verify_workflow_oidc_token(request, allowed_service_account_emails)
            if error is not None:
                return error
            request.workflow_oidc_claims = claims
            return func(request, *args, **kwargs)

        return wrapper

    if view_func is not None:
        return decorator(view_func)
    return decorator
