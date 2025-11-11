"""GCP Cloud Workflows integration for Django."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import google.auth
from google.cloud.workflows import executions_v1
from google.cloud.workflows.executions_v1.types import Execution

from django_gcp.tasks.serializers import serialize

from .exceptions import (
    InvalidWorkflowArgumentsError,
    WorkflowConfigurationError,
    WorkflowExecutionError,
    WorkflowNotFoundError,
)


@dataclass
class WorkflowExecution:
    """Wrapper for GCP Workflow execution response.

    Attributes:
        id: The execution ID (last part of the execution name)
        name: Full execution resource name
        workflow: Workflow resource name
        state: Execution state (ACTIVE, SUCCEEDED, FAILED, CANCELLED)
        start_time: When execution started
        end_time: When execution ended (if completed)
        argument: The JSON argument passed to the workflow
        result: The workflow result (if completed successfully)
    """

    id: str
    name: str
    workflow: str
    state: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    argument: Optional[str] = None
    result: Optional[str] = None

    @classmethod
    def from_execution(cls, execution: Execution) -> "WorkflowExecution":
        """Create WorkflowExecution from GCP Execution proto."""
        # Extract execution ID from name (format: projects/.../locations/.../workflows/.../executions/{id})
        execution_id = execution.name.split("/")[-1]

        return cls(
            id=execution_id,
            name=execution.name,
            workflow=execution.workflow_revision_id or "",
            state=execution.state.name,
            start_time=execution.start_time,
            end_time=execution.end_time if execution.end_time else None,
            argument=execution.argument if execution.argument else None,
            result=execution.result if execution.result else None,
        )


class Workflow:
    """Base class for triggering GCP Cloud Workflows.

    Subclasses must define:
        - workflow_name: The name of the workflow deployed in GCP
        - location: The GCP region where the workflow is deployed

    Example:
        class ProcessUserData(Workflow):
            workflow_name = "process-user-data"
            location = "europe-west1"

        # Invoke the workflow
        execution = ProcessUserData().invoke(user_id=123, action="process")

        # Store execution ID for tracking
        execution_id = execution.id

        # Later: check status
        status = ProcessUserData().get_execution_status(execution_id)

        # Get console URL
        url = ProcessUserData().get_console_url(execution_id)
    """

    workflow_name: str = None
    location: str = None

    def __init__(self):
        """Initialize the workflow client and get project information from credentials."""
        if not self.workflow_name:
            raise WorkflowConfigurationError(f"{self.__class__.__name__} must define 'workflow_name' class attribute")
        if not self.location:
            raise WorkflowConfigurationError(f"{self.__class__.__name__} must define 'location' class attribute")

        # Get default credentials and project ID
        self._credentials, self._project_id = google.auth.default()

        if not self._project_id:
            raise WorkflowConfigurationError(
                "Could not determine project ID from credentials. Ensure GOOGLE_APPLICATION_CREDENTIALS is set."
            )

        # Initialize the Executions client
        self._client = executions_v1.ExecutionsClient(credentials=self._credentials)

    @property
    def project_id(self) -> str:
        """Get the GCP project ID."""
        return self._project_id

    @property
    def workflow_path(self) -> str:
        """Get the full workflow resource path."""
        return f"projects/{self.project_id}/locations/{self.location}/workflows/{self.workflow_name}"

    def invoke(self, **kwargs) -> WorkflowExecution:
        """Invoke the workflow with the given arguments.

        Args:
            **kwargs: Keyword arguments to pass to the workflow as JSON.
                     These will be serialized using Django's JSON encoder.

        Returns:
            WorkflowExecution: Execution object with ID and initial state.

        Raises:
            InvalidWorkflowArgumentsError: If arguments cannot be serialized.
            WorkflowNotFoundError: If the workflow doesn't exist.
            WorkflowExecutionError: If execution creation fails.
        """
        # Serialize arguments to JSON
        try:
            argument_json = serialize(kwargs) if kwargs else None
        except (TypeError, ValueError) as e:
            raise InvalidWorkflowArgumentsError(f"Failed to serialize workflow arguments: {e}") from e

        # Create execution request
        execution = Execution()
        if argument_json:
            execution.argument = argument_json

        # Invoke the workflow
        try:
            response = self._client.create_execution(
                request={
                    "parent": self.workflow_path,
                    "execution": execution,
                }
            )
        except Exception as e:
            error_msg = str(e)
            if "NOT_FOUND" in error_msg or "404" in error_msg:
                raise WorkflowNotFoundError(
                    f"Workflow '{self.workflow_name}' not found in project '{self.project_id}', "
                    f"location '{self.location}'. Ensure the workflow is deployed."
                ) from e
            raise WorkflowExecutionError(f"Failed to invoke workflow '{self.workflow_name}': {error_msg}") from e

        return WorkflowExecution.from_execution(response)

    def get_execution_status(self, execution_id: str) -> WorkflowExecution:
        """Get the current status of a workflow execution.

        Args:
            execution_id: The execution ID returned from invoke().

        Returns:
            WorkflowExecution: Current execution state and details.

        Raises:
            WorkflowExecutionError: If fetching execution status fails.
        """
        execution_name = f"{self.workflow_path}/executions/{execution_id}"

        try:
            execution = self._client.get_execution(name=execution_name)
        except Exception as e:
            raise WorkflowExecutionError(f"Failed to get execution status for '{execution_id}': {e}") from e

        return WorkflowExecution.from_execution(execution)

    def get_console_url(self, execution_id: str) -> str:
        """Get the GCP Console URL for monitoring a workflow execution.

        Args:
            execution_id: The execution ID returned from invoke().

        Returns:
            str: URL to view the execution in GCP Console.
        """
        # Format: https://console.cloud.google.com/workflows/workflow/{location}/{workflow}/execution/{execution_id}?project={project}
        return (
            f"https://console.cloud.google.com/workflows/workflow/"
            f"{self.location}/{self.workflow_name}/execution/{execution_id}"
            f"?project={self.project_id}"
        )
