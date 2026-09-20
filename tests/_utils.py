# Disables for testing:
# pylint: disable=missing-docstring
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods


from contextlib import ExitStack, contextmanager
from functools import wraps
from unittest.mock import patch

from django.urls import reverse
from google.oauth2.service_account import Credentials


def get_admin_add_view_url(cls):
    """Get a url for model class instance add view in the admin
    Provide a Model subclass.
    """
    obj = cls()
    return reverse(f"admin:{obj._meta.app_label}_{type(obj).__name__.lower()}_add")


def get_admin_change_view_url(obj):
    """Get a url for an object's change view in the admin"""
    return reverse(f"admin:{obj._meta.app_label}_{type(obj).__name__.lower()}_change", args=(obj.pk,))


@contextmanager
def authenticated_oidc_caller(email="invoker@example.iam.gserviceaccount.com"):
    """Simulate an authenticated OIDC caller for view tests

    Patches django_gcp.auth.oidc.verify_oidc_token to succeed with verified claims
    for the given service account email, so view tests can exercise behaviour behind
    authentication without any token plumbing. Yields the claims dictionary.
    """
    claims = {"email": email, "email_verified": True}
    with patch("django_gcp.auth.oidc.verify_oidc_token", return_value=(claims, None)):
        yield claims


class patch_auth:  # pylint: disable=invalid-name
    def __init__(self, project_id: str = "potato-dev", location: str = "moon-dark1", email: str = "chuck@norris.com"):
        # Realistic: actual class to be accepted by clients during validation
        # But fake: with as few attributes as possible, any API call using the credential should fail
        credentials = Credentials(
            service_account_email=email,
            signer=None,
            token_uri="",
            project_id=project_id,
        )
        managers = [
            patch("google.auth.default", return_value=(credentials, project_id)),
            patch("django_gcp.tasks.clients.base.GoogleCloudClient._set_location", return_value=location),
        ]
        self.stack = ExitStack()
        for mgr in managers:
            self.stack.enter_context(mgr)

    def __enter__(self):
        return self.stack.__enter__()

    def start(self):
        return self.__enter__()

    def __exit__(self, typ, val, traceback):
        return self.stack.__exit__(typ, val, traceback)

    def stop(self):
        self.__exit__(None, None, None)

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kw):
            with self:
                return func(*args, **kw)

        return wrapper
