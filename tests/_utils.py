# Disables for testing:
# pylint: disable=missing-docstring
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods


from contextlib import contextmanager
from unittest.mock import patch

from django.urls import reverse


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
