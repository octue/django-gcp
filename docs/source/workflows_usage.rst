.. _workflows_usage:

Using Cloud Workflows
=====================

Creating workflow classes
-------------------------

A workflow is created by subclassing the ``Workflow`` class and setting the required class attributes:
``workflow_name`` and ``location``.

.. code-block:: python

    from django_gcp.workflows import Workflow

    class ProcessOrderWorkflow(Workflow):
        workflow_name = "process-order"  # Name of workflow deployed in GCP
        location = "europe-west1"        # Region where workflow is deployed

The workflow definition itself (the YAML/JSON that defines the steps) should be managed separately
via Terraform or other infrastructure-as-code tools. The Django class is only for **invoking** workflows,
not defining them.

Deploying workflow definitions
-------------------------------

Workflow definitions must be deployed to GCP before they can be invoked. Here's an example Terraform
configuration:

.. code-block:: hcl

    resource "google_workflows_workflow" "process_order" {
      name            = "process-order"
      region          = "europe-west1"
      description     = "Processes customer orders through multiple services"
      service_account = google_service_account.workflows_sa.id

      source_contents = file("${path.module}/workflows/process-order.yaml")
    }

The workflow YAML might look like:

.. code-block:: yaml

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

Invoking workflows
------------------

To invoke a workflow, instantiate your workflow class and call the ``invoke()`` method with keyword arguments:

.. code-block:: python

    from myapp.workflows import ProcessOrderWorkflow

    # Invoke the workflow
    execution = ProcessOrderWorkflow().invoke(
        order_id=12345,
        customer_email="user@example.com",
        items=["item1", "item2"],
        total_amount=99.99
    )

    # Store the execution ID for tracking
    execution_id = execution.id

    # Save to database for later reference
    order.workflow_execution_id = execution_id
    order.save()

The ``invoke()`` method returns immediately (asynchronous execution) with a ``WorkflowExecution`` object
containing:

- ``id``: The execution ID for tracking
- ``name``: Full execution resource name
- ``workflow``: Workflow revision ID
- ``state``: Initial state (usually ``ACTIVE``)
- ``start_time``: When execution began

Checking execution status
--------------------------

To check the current status of a workflow execution:

.. code-block:: python

    from myapp.workflows import ProcessOrderWorkflow

    # Get current status
    status = ProcessOrderWorkflow().get_execution_status(execution_id)

    print(f"State: {status.state}")
    print(f"Started: {status.start_time}")

    if status.end_time:
        print(f"Ended: {status.end_time}")

    if status.result:
        print(f"Result: {status.result}")

Execution states include:

- ``ACTIVE``: Workflow is currently running
- ``SUCCEEDED``: Workflow completed successfully
- ``FAILED``: Workflow failed with an error
- ``CANCELLED``: Workflow was cancelled

Getting console URLs
--------------------

For detailed monitoring and debugging, you can get a direct link to the execution in the GCP Console:

.. code-block:: python

    from myapp.workflows import ProcessOrderWorkflow

    console_url = ProcessOrderWorkflow().get_console_url(execution_id)

    # Send to admins for monitoring
    print(f"View execution: {console_url}")

    # Or include in admin panel
    return {
        'execution_id': execution_id,
        'console_url': console_url
    }

Complete example
----------------

Here's a complete example showing workflow invocation and status tracking:

.. code-block:: python

    # workflows.py
    from django_gcp.workflows import Workflow

    class DataPipelineWorkflow(Workflow):
        workflow_name = "data-pipeline"
        location = "us-central1"

.. code-block:: python

    # views.py
    from django.http import JsonResponse
    from .workflows import DataPipelineWorkflow
    from .models import DataJob

    def trigger_data_pipeline(request):
        # Parse request data
        dataset_id = request.POST.get('dataset_id')

        # Invoke the workflow
        try:
            execution = DataPipelineWorkflow().invoke(
                dataset_id=dataset_id,
                processing_mode="full",
                notification_email=request.user.email
            )

            # Store execution info in database
            job = DataJob.objects.create(
                dataset_id=dataset_id,
                workflow_execution_id=execution.id,
                status=execution.state,
                started_at=execution.start_time
            )

            return JsonResponse({
                'job_id': job.id,
                'execution_id': execution.id,
                'console_url': DataPipelineWorkflow().get_console_url(execution.id)
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

.. code-block:: python

    # tasks.py (checking status periodically with a PeriodicTask)
    from django_gcp.tasks import PeriodicTask
    from .workflows import DataPipelineWorkflow
    from .models import DataJob

    class CheckWorkflowStatusTask(PeriodicTask):
        run_every = "*/5 * * * *"  # Every 5 minutes

        def run(self):
            # Find active workflow executions
            active_jobs = DataJob.objects.filter(status='ACTIVE')

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

Error handling
--------------

The workflows module provides specific exceptions for different error scenarios:

.. code-block:: python

    from django_gcp.workflows import (
        Workflow,
        WorkflowNotFoundError,
        WorkflowExecutionError,
        InvalidWorkflowArgumentsError,
        WorkflowConfigurationError
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

Permissions
-----------

To invoke workflows, your service account needs the following IAM permissions:

.. code-block:: hcl

    # Terraform example
    resource "google_project_iam_member" "workflows_invoker" {
      project = var.project_id
      role    = "roles/workflows.invoker"
      member  = "serviceAccount:${var.service_account_email}"
    }

The service account is automatically detected from the ``GOOGLE_APPLICATION_CREDENTIALS``
environment variable.

Best practices
--------------

1. **Store execution IDs**: Always save the execution ID returned from ``invoke()`` so you can track status later.

2. **Use console URLs**: Provide console URLs to admins/operators for detailed debugging and monitoring.

3. **Poll status carefully**: For long-running workflows, implement exponential backoff when polling status
   to avoid hitting API rate limits.

4. **Handle timeouts**: Workflows can run for up to 1 year, so design your status-checking logic accordingly.

5. **Use PeriodicTasks**: For workflows that need status monitoring, use a ``PeriodicTask`` to poll status
   rather than blocking in the request handler.

6. **Validate arguments**: Workflow arguments must be JSON-serializable. Use Django's serializers for complex objects.

7. **Define workflows in IaC**: Keep workflow definitions (YAML) in version-controlled Terraform/infrastructure code,
   not in Django.

Limitations
-----------

- Workflows must be deployed to GCP before they can be invoked from Django
- Only asynchronous (fire-and-forget) invocation is supported - use ``get_execution_status()`` to poll results
- Workflow arguments must be JSON-serializable
- The ``workflow_name`` must exactly match the deployed workflow name in GCP
- The ``location`` must match the region where the workflow is deployed
