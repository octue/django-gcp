# Disables for testing:
# pylint: disable=missing-docstring

import json
from unittest.mock import patch

from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from django_gcp.auth import oidc_required, verify_oidc_token

ALLOWED_EMAIL = "invoker@test-project.iam.gserviceaccount.com"


def _claims(email=ALLOWED_EMAIL, email_verified=True):
    return {"email": email, "email_verified": email_verified}


@override_settings(GCP_INVOKER_SERVICE_ACCOUNT_EMAILS=[ALLOWED_EMAIL])
class VerifyOidcTokenTest(SimpleTestCase):
    """Tests for verify_oidc_token."""

    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, token="a-token", path="/some-endpoint/"):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
        return self.factory.get(path, **headers)

    def test_missing_bearer_token_is_401(self):
        claims, error = verify_oidc_token(self._request(token=None))

        self.assertIsNone(claims)
        self.assertEqual(error.status_code, 401)

    def test_invalid_token_is_401(self):
        with patch("django_gcp.auth.oidc.id_token.verify_oauth2_token", side_effect=ValueError("bad token")):
            claims, error = verify_oidc_token(self._request())

        self.assertIsNone(claims)
        self.assertEqual(error.status_code, 401)

    def test_unverified_email_is_403(self):
        with patch(
            "django_gcp.auth.oidc.id_token.verify_oauth2_token",
            return_value=_claims(email_verified=False),
        ):
            claims, error = verify_oidc_token(self._request())

        self.assertIsNone(claims)
        self.assertEqual(error.status_code, 403)

    def test_unlisted_service_account_is_403(self):
        with patch(
            "django_gcp.auth.oidc.id_token.verify_oauth2_token",
            return_value=_claims(email="someone-else@test-project.iam.gserviceaccount.com"),
        ):
            claims, error = verify_oidc_token(self._request())

        self.assertIsNone(claims)
        self.assertEqual(error.status_code, 403)

    def test_valid_token_returns_claims(self):
        with patch("django_gcp.auth.oidc.id_token.verify_oauth2_token", return_value=_claims()):
            claims, error = verify_oidc_token(self._request())

        self.assertIsNone(error)
        self.assertEqual(claims["email"], ALLOWED_EMAIL)

    def test_audience_is_a_list_of_path_and_full_absolute_uris(self):
        request = self._request()

        with patch("django_gcp.auth.oidc.id_token.verify_oauth2_token", return_value=_claims()) as mock_verify:
            verify_oidc_token(request)

        audience = mock_verify.call_args.kwargs["audience"]
        self.assertEqual(audience, [request.build_absolute_uri(request.path), request.build_absolute_uri()])
        # Without a query string the two audiences coincide
        self.assertEqual(audience[0], audience[1])
        self.assertTrue(audience[0].endswith("/some-endpoint/"))
        self.assertTrue(audience[0].startswith("http"))

    def test_audience_includes_query_string_variant_when_present(self):
        request = self._request(path="/some-endpoint/?category=fruit&name=banana")

        with patch("django_gcp.auth.oidc.id_token.verify_oauth2_token", return_value=_claims()) as mock_verify:
            verify_oidc_token(request)

        audience = mock_verify.call_args.kwargs["audience"]
        self.assertEqual(audience, [request.build_absolute_uri(request.path), request.build_absolute_uri()])
        self.assertNotEqual(audience[0], audience[1])
        self.assertTrue(audience[0].endswith("/some-endpoint/"))
        self.assertTrue(audience[1].endswith("/some-endpoint/?category=fruit&name=banana"))

    def test_explicit_allowed_list_overrides_settings(self):
        other = "other@test-project.iam.gserviceaccount.com"

        with patch("django_gcp.auth.oidc.id_token.verify_oauth2_token", return_value=_claims(email=other)):
            claims, error = verify_oidc_token(self._request(), allowed_service_account_emails=[other])

        self.assertIsNone(error)
        self.assertEqual(claims["email"], other)


class VerifyOidcTokenSettingsResolutionTest(SimpleTestCase):
    """The allow-list resolves through settings_names in order, defaulting to empty (reject everyone)."""

    def _request(self):
        return RequestFactory().get("/some-endpoint/", HTTP_AUTHORIZATION="Bearer a-token")

    def test_absent_setting_rejects_every_caller(self):
        with patch("django_gcp.auth.oidc.id_token.verify_oauth2_token", return_value=_claims()):
            claims, error = verify_oidc_token(self._request())

        self.assertIsNone(claims)
        self.assertEqual(error.status_code, 403)

    @override_settings(
        GCP_WORKFLOWS_INVOKER_SERVICE_ACCOUNT_EMAILS=[ALLOWED_EMAIL],
        GCP_INVOKER_SERVICE_ACCOUNT_EMAILS=["someone-else@test-project.iam.gserviceaccount.com"],
    )
    def test_first_named_setting_wins_when_present(self):
        with patch("django_gcp.auth.oidc.id_token.verify_oauth2_token", return_value=_claims()):
            claims, error = verify_oidc_token(
                self._request(),
                settings_names=("GCP_WORKFLOWS_INVOKER_SERVICE_ACCOUNT_EMAILS", "GCP_INVOKER_SERVICE_ACCOUNT_EMAILS"),
            )

        self.assertIsNone(error)
        self.assertEqual(claims["email"], ALLOWED_EMAIL)

    @override_settings(GCP_INVOKER_SERVICE_ACCOUNT_EMAILS=[ALLOWED_EMAIL])
    def test_falls_back_to_second_named_setting_when_first_absent(self):
        with patch("django_gcp.auth.oidc.id_token.verify_oauth2_token", return_value=_claims()):
            claims, error = verify_oidc_token(
                self._request(),
                settings_names=("GCP_WORKFLOWS_INVOKER_SERVICE_ACCOUNT_EMAILS", "GCP_INVOKER_SERVICE_ACCOUNT_EMAILS"),
            )

        self.assertIsNone(error)
        self.assertEqual(claims["email"], ALLOWED_EMAIL)

    def test_neither_named_setting_present_rejects_every_caller(self):
        with patch("django_gcp.auth.oidc.id_token.verify_oauth2_token", return_value=_claims()):
            claims, error = verify_oidc_token(
                self._request(),
                settings_names=("GCP_WORKFLOWS_INVOKER_SERVICE_ACCOUNT_EMAILS", "GCP_INVOKER_SERVICE_ACCOUNT_EMAILS"),
            )

        self.assertIsNone(claims)
        self.assertEqual(error.status_code, 403)


@override_settings(GCP_INVOKER_SERVICE_ACCOUNT_EMAILS=[ALLOWED_EMAIL])
class OidcRequiredTest(SimpleTestCase):
    """Tests for the oidc_required view decorator."""

    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, token="a-token"):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
        return self.factory.get("/some-endpoint/", **headers)

    def test_bare_decorator_runs_the_view_and_attaches_claims(self):
        @oidc_required
        def view(request):
            return JsonResponse({"email": request.oidc_claims["email"]})

        with patch("django_gcp.auth.oidc.id_token.verify_oauth2_token", return_value=_claims()):
            response = view(self._request())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["email"], ALLOWED_EMAIL)

    def test_failed_verification_short_circuits_the_view(self):
        @oidc_required
        def view(request):  # pragma: no cover - must not run
            raise AssertionError("view should not be called")

        response = view(self._request(token=None))

        self.assertEqual(response.status_code, 401)

    def test_decorator_with_arguments_overrides_allowed_list(self):
        other = "other@test-project.iam.gserviceaccount.com"

        @oidc_required(allowed_service_account_emails=[other])
        def view(request):
            return JsonResponse({"ok": True})

        with patch("django_gcp.auth.oidc.id_token.verify_oauth2_token", return_value=_claims(email=other)):
            response = view(self._request())

        self.assertEqual(response.status_code, 200)

    @override_settings(GCP_WORKFLOWS_INVOKER_SERVICE_ACCOUNT_EMAILS=[ALLOWED_EMAIL])
    def test_decorator_with_settings_names_resolves_from_those_settings(self):
        @oidc_required(settings_names=("GCP_WORKFLOWS_INVOKER_SERVICE_ACCOUNT_EMAILS",))
        def view(request):
            return JsonResponse({"ok": True})

        with patch("django_gcp.auth.oidc.id_token.verify_oauth2_token", return_value=_claims()):
            response = view(self._request())

        self.assertEqual(response.status_code, 200)
