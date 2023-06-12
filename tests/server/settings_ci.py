# Used for CI of the django_gcp module itself
# flake8: noqa
# pylint: disable=wildcard-import,unused-wildcard-import
from .settings import *


# TODO REFACTOR REQUEST
# This is a failed attempt to solve https://github.com/octue/django-gcp/issues/30
# When that is solved, this separate setitngs module may be removable.


LOGGING = {
    **LOGGING,
    "root": {"handlers": ["gcp_structured_logging"]},
    "loggers": {},
}
