class TaskNotRegisteredError(Exception):
    """Raised when a requested task name is not found among the registered tasks"""

    def __init__(self, name: str):
        message = f"Task {name} not registered."
        super().__init__(message)


class IncorrectTaskUsageError(Exception):
    """Raised when one of the Task classes is directly instantiated, instead of subclassed"""


class InvalidEndpointError(Exception):
    """Raised when a specified endpoint isn't valid"""

    def __init__(self, endpoint):
        message = f"The endpoint is invalid for use with a GCP pub/sub push subscription. Endpoints need to be valid and secure. ({endpoint}) "
        super().__init__(message)


class InvalidPubSubMessageError(ValueError):
    """Raised when attempting to decode a Pub/Sub message without valid fields"""


class UnknownActionError(ValueError):
    """Raised when attempting to create or use a resource not known to django-gcp"""


class DuplicateTaskError(Exception):
    """Raised when a unique (non-duplicatable) task is enqueued but already present in the queue"""


class AttemptedOverwriteError(Exception):
    """Raised when attempting to overwrite an existing object in GCS with another object"""


class MissingBlobError(Exception):
    """Raised when attempting to access or copy a blob that is not present in GCS"""


class IncompatibleSettingsError(ValueError):
    """Raised when settings values are mutually exclusive"""
