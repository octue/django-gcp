# Using Cloud Workflows

## Creating workflow classes

A workflow is created by subclassing the `Workflow` class and setting the required class
attributes, `workflow_name` and `location`:

```python
from django_gcp.workflows import Workflow

class ProcessOrderWorkflow(Workflow):
    workflow_name = "process-order"  # Name of workflow deployed in GCP
    location = "europe-west1"        # Region where workflow is deployed
```

The workflow definition itself (the YAML or JSON that defines the steps) should be managed
separately via Terraform or other infrastructure-as-code tools. The Django class is only for
**invoking** workflows, not defining them.

## Deploying workflow definitions

Workflow definitions must be deployed to GCP before they can be invoked. Here is an example
Terraform configuration:

```hcl
resource "google_workflows_workflow" "process_order" {
  name            = "process-order"
  region          = "europe-west1"
  description     = "Processes customer orders through multiple services"
  service_account = google_service_account.workflows_sa.id

  source_contents = file("${path.module}/workflows/process-order.yaml")
}
```

The workflow YAML might look like:

```yaml
main:
  params: [args]
  steps:
    - validate_order:
        call: http.post
        args:
          url: https://api.example.com/validate
          body: ${args}
    - process_payment:
        call: http.post
        args:
          url: https://api.example.com/payments
          body: ${args}
    - send_confirmation:
        call: http.post
        args:
          url: https://api.example.com/emails
          body:
            email: ${args.customer_email}
            order_id: ${args.order_id}
```

## Invoking workflows

To invoke a workflow, instantiate your workflow class and call the `invoke()` method with
keyword arguments:

```python
from myapp.workflows import ProcessOrderWorkflow

# Invoke the workflow
execution = ProcessOrderWorkflow().invoke(
    order_id=12345,
    customer_email="user@example.com",
    items=["item1", "item2"],
    total_amount=99.99,
)

# Store the execution ID for tracking
execution_id = execution.id

# Save to database for later reference
order.workflow_execution_id = execution_id
order.save()
```

The `invoke()` method returns immediately (asynchronous execution) with a `WorkflowExecution`
object containing:

- `id`: the execution ID for tracking,
- `name`: the full execution resource name,
- `workflow`: the workflow revision ID,
- `state`: the initial state (usually `ACTIVE`), and
- `start_time`: when execution began.

## Checking execution status

To check the current status of a workflow execution:

```python
from myapp.workflows import ProcessOrderWorkflow

# Get current status
status = ProcessOrderWorkflow().get_execution_status(execution_id)

print(f"State: {status.state}")
print(f"Started: {status.start_time}")

if status.end_time:
    print(f"Ended: {status.end_time}")

if status.result:
    print(f"Result: {status.result}")
```

Execution states include:

- `ACTIVE`: the workflow is currently running,
- `SUCCEEDED`: the workflow completed successfully,
- `FAILED`: the workflow failed with an error, and
- `CANCELLED`: the workflow was cancelled.

## Getting console URLs

For detailed monitoring and debugging, you can get a direct link to the execution in the GCP
Console:

```python
from myapp.workflows import ProcessOrderWorkflow

console_url = ProcessOrderWorkflow().get_console_url(execution_id)

# Send to admins for monitoring
print(f"View execution: {console_url}")

# Or include in admin panel
return {
    "execution_id": execution_id,
    "console_url": console_url,
}
```

## Complete example

Here is a complete example showing workflow invocation and status tracking:

```python
# workflows.py
from django_gcp.workflows import Workflow

class DataPipelineWorkflow(Workflow):
    workflow_name = "data-pipeline"
    location = "us-central1"
```

```python
# views.py
from django.http import JsonResponse
from .workflows import DataPipelineWorkflow
from .models import DataJob

def trigger_data_pipeline(request):
    # Parse request data
    dataset_id = request.POST.get("dataset_id")

    # Invoke the workflow
    try:
        execution = DataPipelineWorkflow().invoke(
            dataset_id=dataset_id,
            processing_mode="full",
            notification_email=request.user.email,
        )

        # Store execution info in database
        job = DataJob.objects.create(
            dataset_id=dataset_id,
            workflow_execution_id=execution.id,
            status=execution.state,
            started_at=execution.start_time,
        )

        return JsonResponse({
            "job_id": job.id,
            "execution_id": execution.id,
            "console_url": DataPipelineWorkflow().get_console_url(execution.id),
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
```

```python
# tasks.py (checking status periodically with a PeriodicTask)
from django_gcp.tasks import PeriodicTask
from .workflows import DataPipelineWorkflow
from .models import DataJob

class CheckWorkflowStatusTask(PeriodicTask):
    run_every = "*/5 * * * *"  # Every 5 minutes

    def run(self):
        # Find active workflow executions
        active_jobs = DataJob.objects.filter(status="ACTIVE")

        for job in active_jobs:
            # Check status
            status = DataPipelineWorkflow().get_execution_status(
                job.workflow_execution_id
            )

            # Update job record
            job.status = status.state
            if status.end_time:
                job.completed_at = status.end_time
            if status.result:
                job.result = status.result
            job.save()
```

## Error handling

The workflows module provides specific exceptions for different error scenarios:

```python
from django_gcp.workflows import (
    Workflow,
    WorkflowNotFoundError,
    WorkflowExecutionError,
    InvalidWorkflowArgumentsError,
    WorkflowConfigurationError,
)

class MyWorkflow(Workflow):
    workflow_name = "my-workflow"
    location = "us-central1"

try:
    execution = MyWorkflow().invoke(data="test")
except WorkflowNotFoundError:
    # Workflow doesn't exist in GCP
    print("Workflow not deployed - check Terraform")
except InvalidWorkflowArgumentsError:
    # Arguments couldn't be serialized to JSON
    print("Invalid arguments")
except WorkflowExecutionError as e:
    # Other execution errors
    print(f"Execution failed: {e}")
```

## Permissions

To invoke workflows, your service account needs the following IAM permissions:

```hcl
# Terraform example
resource "google_project_iam_member" "workflows_invoker" {
  project = var.project_id
  role    = "roles/workflows.invoker"
  member  = "serviceAccount:${var.service_account_email}"
}
```

The service account is automatically detected from the `GOOGLE_APPLICATION_CREDENTIALS`
environment variable.

## Verifying calls made by workflows

Multi-step workflows often need to call back into Django between steps (for example to fetch
state a Cloud Run job cannot return). Cloud Workflows can authenticate those calls with an
OIDC identity token (`auth: {type: OIDC, audience: <url>}`); platform IAM may gate the
intended route, but if the same application is also served publicly you must verify the token
in-app as well. `django_gcp` provides both a view decorator and the underlying function:

```python
from django_gcp.workflows import workflow_oidc_required

@workflow_oidc_required
def pending_items(request):
    # request.workflow_oidc_claims carries the verified token claims
    return JsonResponse({"pending": [...]})
```

Verification requires a valid signature, an audience exactly matching the request's absolute
URI, and a verified email in the allowed caller list, configured as:

```python
GCP_WORKFLOWS_INVOKER_SERVICE_ACCOUNT_EMAILS = ["workflows@my-project.iam.gserviceaccount.com"]
```

With the setting absent, every caller is rejected. Pass `allowed_service_account_emails` to
the decorator (or to `verify_workflow_oidc_token(request)` directly) to override the setting
per-endpoint. For the wider context on securing endpoints, see
[Authenticating events and tasks](../authentication/events-and-tasks.md).

## Best practices

1. **Store execution IDs**: always save the execution ID returned from `invoke()` so you can
   track status later.
2. **Use console URLs**: provide console URLs to admins and operators for detailed debugging
   and monitoring.
3. **Poll status carefully**: for long-running workflows, implement exponential backoff when
   polling status, to avoid hitting API rate limits.
4. **Handle timeouts**: workflows can run for up to one year, so design your status-checking
   logic accordingly.
5. **Use periodic tasks**: for workflows that need status monitoring, use a `PeriodicTask` to
   poll status rather than blocking in the request handler.
6. **Validate arguments**: workflow arguments must be JSON-serialisable. Use Django's
   serializers for complex objects.
7. **Define workflows in infrastructure code**: keep workflow definitions (YAML) in
   version-controlled Terraform or other infrastructure code, not in Django.

## Limitations

- Workflows must be deployed to GCP before they can be invoked from Django.
- Only asynchronous (fire-and-forget) invocation is supported; use `get_execution_status()`
  to poll results.
- Workflow arguments must be JSON-serialisable.
- The `workflow_name` must exactly match the deployed workflow name in GCP.
- The `location` must match the region where the workflow is deployed.
