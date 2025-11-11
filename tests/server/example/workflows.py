"""Example workflows for testing."""

from django_gcp.workflows import Workflow


class SampleWorkflow(Workflow):
    """Sample workflow for testing workflow invocation and status checking.

    This workflow runs for a configurable duration and either succeeds or fails
    based on the arguments provided.

    Args:
        duration: Number of seconds the workflow should run (default: 5)
        should_fail: Whether the workflow should fail (default: False)
    """

    workflow_name = "sample-workflow"
    location = "europe-west1"
