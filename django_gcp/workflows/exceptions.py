"""Custom exceptions for GCP Cloud Workflows."""


class WorkflowError(Exception):
    """Base exception for workflow-related errors."""

    pass


class WorkflowNotFoundError(WorkflowError):
    """Raised when a workflow cannot be found in GCP."""

    pass


class WorkflowExecutionError(WorkflowError):
    """Raised when workflow execution fails."""

    pass


class InvalidWorkflowArgumentsError(WorkflowError):
    """Raised when workflow arguments are invalid or cannot be serialized."""

    pass


class WorkflowConfigurationError(WorkflowError):
    """Raised when workflow configuration is invalid or incomplete."""

    pass
