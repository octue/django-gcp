# Disables for testing:
# pylint: disable=missing-docstring
# pylint: disable=protected-access

from datetime import datetime
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from django_gcp.workflows import (
    InvalidWorkflowArgumentsError,
    Workflow,
    WorkflowConfigurationError,
    WorkflowExecution,
    WorkflowExecutionError,
    WorkflowNotFoundError,
)


class SampleWorkflow(Workflow):
    """Sample workflow class for unit tests."""

    workflow_name = "test-workflow"
    location = "europe-west1"


class WorkflowExecutionTest(SimpleTestCase):
    """Tests for WorkflowExecution dataclass."""

    def test_from_execution_basic(self):
        """Test creating WorkflowExecution from GCP Execution proto."""
        mock_execution = MagicMock()
        mock_execution.name = "projects/test-project/locations/europe-west1/workflows/test-workflow/executions/exec-123"
        mock_execution.workflow_revision_id = "test-workflow-rev-1"
        mock_execution.state.name = "ACTIVE"
        mock_execution.start_time = datetime(2025, 1, 1, 12, 0, 0)
        mock_execution.end_time = None
        mock_execution.argument = '{"key": "value"}'
        mock_execution.result = None

        workflow_execution = WorkflowExecution.from_execution(mock_execution)

        self.assertEqual(workflow_execution.id, "exec-123")
        self.assertEqual(workflow_execution.name, mock_execution.name)
        self.assertEqual(workflow_execution.workflow, "test-workflow-rev-1")
        self.assertEqual(workflow_execution.state, "ACTIVE")
        self.assertEqual(workflow_execution.start_time, datetime(2025, 1, 1, 12, 0, 0))
        self.assertIsNone(workflow_execution.end_time)
        self.assertEqual(workflow_execution.argument, '{"key": "value"}')
        self.assertIsNone(workflow_execution.result)

    def test_from_execution_completed(self):
        """Test creating WorkflowExecution from completed execution."""
        mock_execution = MagicMock()
        mock_execution.name = "projects/test-project/locations/europe-west1/workflows/test-workflow/executions/exec-456"
        mock_execution.workflow_revision_id = "test-workflow-rev-1"
        mock_execution.state.name = "SUCCEEDED"
        mock_execution.start_time = datetime(2025, 1, 1, 12, 0, 0)
        mock_execution.end_time = datetime(2025, 1, 1, 12, 5, 0)
        mock_execution.argument = '{"input": "data"}'
        mock_execution.result = '{"output": "result"}'

        workflow_execution = WorkflowExecution.from_execution(mock_execution)

        self.assertEqual(workflow_execution.id, "exec-456")
        self.assertEqual(workflow_execution.state, "SUCCEEDED")
        self.assertEqual(workflow_execution.end_time, datetime(2025, 1, 1, 12, 5, 0))
        self.assertEqual(workflow_execution.result, '{"output": "result"}')


class WorkflowConfigurationTest(SimpleTestCase):
    """Tests for Workflow configuration and initialization."""

    @patch("google.auth.default")
    def test_workflow_requires_workflow_name(self, mock_auth):
        """Test that Workflow class requires workflow_name attribute."""
        mock_auth.return_value = (MagicMock(), "test-project")

        class InvalidWorkflow(Workflow):
            location = "europe-west1"

        with self.assertRaises(WorkflowConfigurationError) as context:
            InvalidWorkflow()

        self.assertIn("workflow_name", str(context.exception))

    @patch("google.auth.default")
    def test_workflow_requires_location(self, mock_auth):
        """Test that Workflow class requires location attribute."""
        mock_auth.return_value = (MagicMock(), "test-project")

        class InvalidWorkflow(Workflow):
            workflow_name = "test-workflow"

        with self.assertRaises(WorkflowConfigurationError) as context:
            InvalidWorkflow()

        self.assertIn("location", str(context.exception))

    @patch("google.auth.default")
    def test_workflow_requires_project_id_from_credentials(self, mock_auth):
        """Test that Workflow raises error if project_id cannot be determined."""
        mock_auth.return_value = (MagicMock(), None)

        with self.assertRaises(WorkflowConfigurationError) as context:
            SampleWorkflow()

        self.assertIn("project ID", str(context.exception))

    @patch("django_gcp.workflows.workflows.executions_v1.ExecutionsClient")
    @patch("google.auth.default")
    def test_workflow_initializes_with_credentials(self, mock_auth, mock_client_class):
        """Test that Workflow initializes ExecutionsClient with credentials."""
        mock_credentials = MagicMock()
        mock_auth.return_value = (mock_credentials, "test-project")

        workflow = SampleWorkflow()

        self.assertEqual(workflow.project_id, "test-project")
        self.assertEqual(workflow.workflow_path, "projects/test-project/locations/europe-west1/workflows/test-workflow")
        mock_client_class.assert_called_once_with(credentials=mock_credentials)


class WorkflowInvokeTest(SimpleTestCase):
    """Tests for Workflow.invoke() method."""

    @patch("django_gcp.workflows.workflows.executions_v1.ExecutionsClient")
    @patch("google.auth.default")
    def test_invoke_workflow_success(self, mock_auth, mock_client_class):
        """Test successfully invoking a workflow."""
        mock_auth.return_value = (MagicMock(), "test-project")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock the execution response
        mock_response = MagicMock()
        mock_response.name = "projects/test-project/locations/europe-west1/workflows/test-workflow/executions/exec-123"
        mock_response.workflow_revision_id = "test-workflow-rev-1"
        mock_response.state.name = "ACTIVE"
        mock_response.start_time = datetime(2025, 1, 1, 12, 0, 0)
        mock_response.end_time = None
        mock_response.argument = '{"user_id": 123, "action": "process"}'
        mock_response.result = None
        mock_client.create_execution.return_value = mock_response

        workflow = SampleWorkflow()
        result = workflow.invoke(user_id=123, action="process")

        self.assertIsInstance(result, WorkflowExecution)
        self.assertEqual(result.id, "exec-123")
        self.assertEqual(result.state, "ACTIVE")

        # Verify create_execution was called correctly
        mock_client.create_execution.assert_called_once()
        call_kwargs = mock_client.create_execution.call_args.kwargs
        self.assertEqual(
            call_kwargs["request"]["parent"], "projects/test-project/locations/europe-west1/workflows/test-workflow"
        )
        # Check that argument was set (exact JSON format may vary)
        self.assertIn("user_id", call_kwargs["request"]["execution"].argument)

    @patch("django_gcp.workflows.workflows.executions_v1.ExecutionsClient")
    @patch("google.auth.default")
    def test_invoke_workflow_without_arguments(self, mock_auth, mock_client_class):
        """Test invoking a workflow without arguments."""
        mock_auth.return_value = (MagicMock(), "test-project")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.name = "projects/test-project/locations/europe-west1/workflows/test-workflow/executions/exec-456"
        mock_response.workflow_revision_id = ""
        mock_response.state.name = "ACTIVE"
        mock_response.start_time = datetime(2025, 1, 1, 12, 0, 0)
        mock_response.end_time = None
        mock_response.argument = None
        mock_response.result = None
        mock_client.create_execution.return_value = mock_response

        workflow = SampleWorkflow()
        result = workflow.invoke()

        self.assertEqual(result.id, "exec-456")
        mock_client.create_execution.assert_called_once()

    @patch("django_gcp.workflows.workflows.executions_v1.ExecutionsClient")
    @patch("google.auth.default")
    def test_invoke_workflow_not_found(self, mock_auth, mock_client_class):
        """Test invoking a workflow that doesn't exist."""
        mock_auth.return_value = (MagicMock(), "test-project")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.create_execution.side_effect = Exception("404 NOT_FOUND: Workflow not found")

        workflow = SampleWorkflow()

        with self.assertRaises(WorkflowNotFoundError) as context:
            workflow.invoke(user_id=123)

        self.assertIn("test-workflow", str(context.exception))
        self.assertIn("test-project", str(context.exception))
        self.assertIn("europe-west1", str(context.exception))

    @patch("django_gcp.workflows.workflows.executions_v1.ExecutionsClient")
    @patch("google.auth.default")
    def test_invoke_workflow_execution_error(self, mock_auth, mock_client_class):
        """Test handling generic execution errors."""
        mock_auth.return_value = (MagicMock(), "test-project")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.create_execution.side_effect = Exception("Some other error")

        workflow = SampleWorkflow()

        with self.assertRaises(WorkflowExecutionError) as context:
            workflow.invoke(user_id=123)

        self.assertIn("test-workflow", str(context.exception))

    @patch("django_gcp.workflows.workflows.executions_v1.ExecutionsClient")
    @patch("google.auth.default")
    def test_invoke_workflow_with_non_serializable_arguments(self, mock_auth, mock_client_class):
        """Test invoking a workflow with arguments that cannot be serialized to JSON."""
        mock_auth.return_value = (MagicMock(), "test-project")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        workflow = SampleWorkflow()

        # Pass a non-serializable object (lambda function)
        with self.assertRaises(InvalidWorkflowArgumentsError) as context:
            workflow.invoke(callback=lambda x: x)

        # Verify error message mentions serialization
        self.assertIn("serialize", str(context.exception).lower())

        # Verify the original exception is preserved in the chain
        self.assertIsNotNone(context.exception.__cause__)


class WorkflowStatusTest(SimpleTestCase):
    """Tests for Workflow.get_execution_status() method."""

    @patch("django_gcp.workflows.workflows.executions_v1.ExecutionsClient")
    @patch("google.auth.default")
    def test_get_execution_status_success(self, mock_auth, mock_client_class):
        """Test getting execution status successfully."""
        mock_auth.return_value = (MagicMock(), "test-project")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_execution = MagicMock()
        mock_execution.name = "projects/test-project/locations/europe-west1/workflows/test-workflow/executions/exec-123"
        mock_execution.workflow_revision_id = "test-workflow-rev-1"
        mock_execution.state.name = "SUCCEEDED"
        mock_execution.start_time = datetime(2025, 1, 1, 12, 0, 0)
        mock_execution.end_time = datetime(2025, 1, 1, 12, 5, 0)
        mock_execution.argument = '{"user_id": 123}'
        mock_execution.result = '{"status": "completed"}'
        mock_client.get_execution.return_value = mock_execution

        workflow = SampleWorkflow()
        status = workflow.get_execution_status("exec-123")

        self.assertEqual(status.id, "exec-123")
        self.assertEqual(status.state, "SUCCEEDED")
        self.assertEqual(status.result, '{"status": "completed"}')

        mock_client.get_execution.assert_called_once_with(
            name="projects/test-project/locations/europe-west1/workflows/test-workflow/executions/exec-123"
        )

    @patch("django_gcp.workflows.workflows.executions_v1.ExecutionsClient")
    @patch("google.auth.default")
    def test_get_execution_status_error(self, mock_auth, mock_client_class):
        """Test handling errors when getting execution status."""
        mock_auth.return_value = (MagicMock(), "test-project")
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.get_execution.side_effect = Exception("Execution not found")

        workflow = SampleWorkflow()

        with self.assertRaises(WorkflowExecutionError) as context:
            workflow.get_execution_status("exec-invalid")

        self.assertIn("exec-invalid", str(context.exception))


class WorkflowConsoleUrlTest(SimpleTestCase):
    """Tests for Workflow.get_console_url() method."""

    @patch("django_gcp.workflows.workflows.executions_v1.ExecutionsClient")
    @patch("google.auth.default")
    def test_get_console_url(self, mock_auth, mock_client_class):
        """Test generating GCP Console URL."""
        mock_auth.return_value = (MagicMock(), "test-project")
        mock_client_class.return_value = MagicMock()

        workflow = SampleWorkflow()
        url = workflow.get_console_url("exec-123")

        expected_url = (
            "https://console.cloud.google.com/workflows/workflow/"
            "europe-west1/test-workflow/execution/exec-123"
            "?project=test-project"
        )
        self.assertEqual(url, expected_url)

    @patch("django_gcp.workflows.workflows.executions_v1.ExecutionsClient")
    @patch("google.auth.default")
    def test_get_console_url_different_location(self, mock_auth, mock_client_class):
        """Test console URL generation with different location."""
        mock_auth.return_value = (MagicMock(), "my-project")
        mock_client_class.return_value = MagicMock()

        class UsWorkflow(Workflow):
            workflow_name = "us-workflow"
            location = "us-central1"

        workflow = UsWorkflow()
        url = workflow.get_console_url("exec-456")

        expected_url = (
            "https://console.cloud.google.com/workflows/workflow/"
            "us-central1/us-workflow/execution/exec-456"
            "?project=my-project"
        )
        self.assertEqual(url, expected_url)
