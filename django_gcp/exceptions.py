class TaskNotRegisteredError(Exception):
    """Raised when a requested task name is not found among the registered tasks"""

    def __init__(self, name: str):
        message = f"Task {name} not registered."
        super().__init__(message)


class IncorrectTaskUsageError(Exception):
    """Raised when one of the Task classes is directly instantiated, instead of subclassed"""


class InvalidTaskDomainError(Exception):
    """Raised when the specified tasks domain isn't valid"""

    def __init__(self, endpoint):
        message = f"The GCP_TASKS_DOMAIN setting is invalid for use with GCP Tasks or PubSub push subscriptions. Domain must use https:// protocol in production. Given value: {endpoint}"
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
