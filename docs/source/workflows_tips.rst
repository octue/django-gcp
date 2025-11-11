.. _workflows_tips:

Workflows Tips and Patterns
============================

This page contains helpful patterns and tips for using Cloud Workflows with django-gcp.

Invoking Cloud Run Jobs from Workflows
---------------------------------------

.. tip::

    A powerful pattern is using workflows to invoke **Cloud Run Jobs** that run Django management commands.
    This is particularly useful for long-running or resource-intensive management commands that shouldn't
    run in your web server.

If you have a Django app deployed as a Cloud Run Job (in addition to or instead of a Cloud Run Service),
you can create workflows that invoke these jobs to run management commands.

**Example workflow definition** (``workflows/run-management-command.yaml``):

.. code-block:: yaml

    main:
      params: [args]
      steps:
        - init:
            assign:
              - project_id: "my-project"
              - job_location: "europe-west1"
              - job_name: ${"namespaces/" + project_id + "/jobs/django-job"}

        - run_django_command:
            call: googleapis.run.v1.namespaces.jobs.run
            args:
              name: ${job_name}
              location: ${job_location}
              body:
                overrides:
                  containerOverrides:
                    args:
                      # You may not need "python" if it's already defined as your container command
                      - "python"
                      - "manage.py"
                      - ${args.command}
                      - ${args.command_args}
            result: job_execution

        - finish:
            return: ${job_execution}

**Django workflow class:**

.. code-block:: python

    from django_gcp.workflows import Workflow

    class RunManagementCommandWorkflow(Workflow):
        workflow_name = "run-management-command"
        location = "europe-west1"

**Invoking from Django:**

.. code-block:: python

    # Run a management command via Cloud Run Job
    execution = RunManagementCommandWorkflow().invoke(
        command="import_data",
        command_args="--source=production"
    )

    # Track the execution
    print(f"Job started: {execution.id}")
    print(f"Monitor: {RunManagementCommandWorkflow().get_console_url(execution.id)}")

**Benefits of this pattern:**

- Run management commands without blocking web requests
- Handle commands that need more memory/CPU than web instances
- Leverage workflow features like retries, error handling, and conditional logic
- Orchestrate multiple management commands in sequence
- Keep web servers optimized for HTTP traffic while jobs handle batch processing

**Example use cases:**

- Data imports/exports
- Database migrations on large datasets
- Report generation
- Batch email sending
- Cache warming
- Cleanup operations
