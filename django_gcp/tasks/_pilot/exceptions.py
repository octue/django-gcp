from typing import List


class UnsupportedFormatException(Exception):
    pass


class ValidationError(Exception):
    pass


class UnboundException(Exception):
    pass


class NotFound(Exception):
    pass


class FailedPrecondition(Exception):
    pass


class DeletedRecently(FailedPrecondition):
    def __init__(self, resource, blocked_period="1 week"):
        message = f"{resource} was probably deleted recently. Cannot reuse name for {blocked_period}."
        super().__init__(message)


class BigQueryJobError(Exception):
    def __init__(self, job):
        message = " | ".join([error["message"] for error in job.errors])
        super().__init__(message)


class AlreadyExists(Exception):
    pass


class AlreadyDeleted(Exception):
    pass


class NotAllowed(Exception):
    pass


class InvalidPassword(Exception):
    pass


class MissingUserIdentification(Exception):
    pass


class PushWebhookInvalid(ValidationError):
    pass


class ChannelIdNotUnique(Exception):
    pass


class NotACalendarUser(Exception):
    pass


class QuotaExceeded(Exception):
    pass


class OperationError(Exception):
    def __init__(self, errors: List):
        self.errors = errors
        super().__init__(str(self.errors))
