# Disables for testing:
# pylint: disable=missing-docstring

import json
from unittest.mock import patch

from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from django_gcp.workflows import verify_workflow_oidc_token, workflow_oidc_required

ALLOWED_EMAIL = "workflows@test-project.iam.gserviceaccount.com"


def _claims(email=ALLOWED_EMAIL, email_verified=True):
    return {"email": email, "email_verified": email_verified}


@override_settings(GCP_WORKFLOWS_INVOKER_SERVICE_ACCOUNT_EMAILS=[ALLOWED_EMAIL])
class VerifyWorkflowOidcTokenTest(SimpleTestCase):
    """Tests for verify_workflow_oidc_token."""

    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, token="a-token"):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
        return self.factory.get("/workflows/some-endpoint/", **headers)

    def test_missing_bearer_token_is_401(self):
        claims, error = verify_workflow_oidc_token(self._request(token=None))

        self.assertIsNone(claims)
        self.assertEqual(error.status_code, 401)

    def test_invalid_token_is_401(self):
        with patch("django_gcp.workflows.oidc.id_token.verify_oauth2_token", side_effect=ValueError("bad token")):
            claims, error = verify_workflow_oidc_token(self._request())

        self.assertIsNone(claims)
        self.assertEqual(error.status_code, 401)

    def test_unverified_email_is_403(self):
        with patch(
            "django_gcp.workflows.oidc.id_token.verify_oauth2_token",
            return_value=_claims(email_verified=False),
        ):
            claims, error = verify_workflow_oidc_token(self._request())

        self.assertIsNone(claims)
        self.assertEqual(error.status_code, 403)

    def test_unlisted_service_account_is_403(self):
        with patch(
            "django_gcp.workflows.oidc.id_token.verify_oauth2_token",
            return_value=_claims(email="someone-else@test-project.iam.gserviceaccount.com"),
        ):
            claims, error = verify_workflow_oidc_token(self._request())

        self.assertIsNone(claims)
        self.assertEqual(error.status_code, 403)

    def test_valid_token_returns_claims(self):
        with patch("django_gcp.workflows.oidc.id_token.verify_oauth2_token", return_value=_claims()):
            claims, error = verify_workflow_oidc_token(self._request())

        self.assertIsNone(error)
        self.assertEqual(claims["email"], ALLOWED_EMAIL)

    def test_audience_is_the_request_absolute_uri(self):
        with patch("django_gcp.workflows.oidc.id_token.verify_oauth2_token", return_value=_claims()) as mock_verify:
            verify_workflow_oidc_token(self._request())

        audience = mock_verify.call_args.kwargs["audience"]
        self.assertTrue(audience.endswith("/workflows/some-endpoint/"))
        self.assertTrue(audience.startswith("http"))

    def test_explicit_allowed_list_overrides_settings(self):
        other = "other@test-project.iam.gserviceaccount.com"

        with patch("django_gcp.workflows.oidc.id_token.verify_oauth2_token", return_value=_claims(email=other)):
            claims, error = verify_workflow_oidc_token(self._request(), allowed_service_account_emails=[other])

        self.assertIsNone(error)
        self.assertEqual(claims["email"], other)


class VerifyWorkflowOidcTokenDefaultSettingsTest(SimpleTestCase):
    """Without GCP_WORKFLOWS_INVOKER_SERVICE_ACCOUNT_EMAILS defined, every caller is rejected."""

    def test_absent_setting_rejects_every_caller(self):
        request = RequestFactory().get("/workflows/some-endpoint/", HTTP_AUTHORIZATION="Bearer a-token")

        with patch("django_gcp.workflows.oidc.id_token.verify_oauth2_token", return_value=_claims()):
            claims, error = verify_workflow_oidc_token(request)

        self.assertIsNone(claims)
        self.assertEqual(error.status_code, 403)


@override_settings(GCP_WORKFLOWS_INVOKER_SERVICE_ACCOUNT_EMAILS=[ALLOWED_EMAIL])
class WorkflowOidcRequiredTest(SimpleTestCase):
    """Tests for the workflow_oidc_required view decorator."""

    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, token="a-token"):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
        return self.factory.get("/workflows/some-endpoint/", **headers)

    def test_bare_decorator_runs_the_view_and_attaches_claims(self):
        @workflow_oidc_required
        def view(request):
            return JsonResponse({"email": request.workflow_oidc_claims["email"]})

        with patch("django_gcp.workflows.oidc.id_token.verify_oauth2_token", return_value=_claims()):
            response = view(self._request())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["email"], ALLOWED_EMAIL)

    def test_failed_verification_short_circuits_the_view(self):
        @workflow_oidc_required
        def view(request):  # pragma: no cover - must not run
            raise AssertionError("view should not be called")

        response = view(self._request(token=None))

        self.assertEqual(response.status_code, 401)

    def test_decorator_with_arguments_overrides_allowed_list(self):
        other = "other@test-project.iam.gserviceaccount.com"

        @workflow_oidc_required(allowed_service_account_emails=[other])
        def view(request):
            return JsonResponse({"ok": True})

        with patch("django_gcp.workflows.oidc.id_token.verify_oauth2_token", return_value=_claims(email=other)):
            response = view(self._request())

        self.assertEqual(response.status_code, 200)
