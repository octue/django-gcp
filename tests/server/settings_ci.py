# Used for CI of the django_gcp module itself
# flake8: noqa
# pylint: disable=wildcard-import,unused-wildcard-import
from .settings import *


LOGGING = {
    **LOGGING,
    "root": {"handlers": ["gcp_structured_logging"]},
    "loggers": {},
}
