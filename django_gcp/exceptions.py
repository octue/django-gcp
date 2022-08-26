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


class UnknownResourceKindError(ValueError):
    """Raised when attempting to create or use a resource not known to django-gcp"""
