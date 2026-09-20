class FailedPrecondition(Exception):
    pass


class DoesNotExist(Exception):
    def __init__(self, resource):
        message = f"{resource} does not exist."
        super().__init__(message)


class DeletedRecently(FailedPrecondition):
    def __init__(self, resource, blocked_period="1 week"):
        message = f"{resource} was probably deleted recently. Cannot reuse name for {blocked_period}."
        super().__init__(message)
