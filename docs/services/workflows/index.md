# About Cloud Workflows

[Google Cloud Workflows](https://cloud.google.com/workflows) is a fully managed orchestration
platform that executes services and APIs in a defined order to accomplish a specific goal.
Workflows are particularly useful for coordinating multi-step processes, handling complex
business logic, and integrating multiple cloud services.

`django-gcp` provides a simple interface to invoke workflows deployed in GCP, track their
execution status, and monitor them via the GCP Console. See [Usage](usage.md) to get started
and [Tips](tips.md) for useful patterns.

## What are workflows?

A workflow is a series of steps (written in YAML or JSON) that define your business process.
Each step can call an API, invoke a Cloud Run service or function, query a database, or
perform computations. Workflows support:

- **Conditional logic**: branch based on data or results.
- **Loops and iterations**: process lists or retry operations.
- **Error handling**: catch and handle failures gracefully.
- **Sub-workflows**: compose reusable workflow components.
- **Long-running operations**: execute for up to one year.

## Workflows vs tasks

Both workflows and [tasks](../tasks/index.md) are used for asynchronous operations, but they
serve different purposes.

**Cloud Tasks** (via `OnDemandTask` in `django-gcp`) makes a single HTTP request to an
endpoint, with stateless execution lasting up to 30 minutes. It is best for individual
background jobs, API calls, and simple task queuing.

**Cloud Workflows** (via `Workflow` in `django-gcp`) provides multi-step orchestration with
state management and complex control flow (conditionals, loops, error handling), running for
up to one year. It is best for multi-service coordination, complex business processes, and
long-running orchestrations.

Use Cloud Workflows when you are:

- coordinating multiple API calls across services,
- implementing complex business processes with branching logic,
- building approval workflows or human-in-the-loop processes,
- orchestrating data pipelines with dependencies,
- handling long-running batch operations, or
- implementing saga patterns for distributed transactions.

Use Cloud Tasks when you are:

- queueing individual background jobs,
- rate-limiting API calls,
- distributing work across instances,
- performing simple fire-and-forget operations, or
- scheduling tasks with retries.

## Why `django-gcp` for workflows?

The `django_gcp.workflows` module provides:

1. **Simple Django integration**: define workflows as Python classes, similar to tasks.
2. **Type-safe arguments**: automatic JSON serialisation using Django's serializers.
3. **Execution tracking**: get execution IDs for monitoring and status checks.
4. **Console URLs**: easy access to the GCP Console for detailed execution views.
5. **Infrastructure as code**: workflows defined in Terraform, invoked from Django.
6. **A consistent API**: the same patterns as other `django-gcp` modules.

## No complex setup required

Traditional workflow engines (Airflow, Temporal, and so on) require self-hosted
infrastructure, database setup, worker management, and complex deployment pipelines.

Cloud Workflows via `django-gcp` only requires:

- a workflow definition in your Terraform or other infrastructure code,
- a service account with workflow execution permissions (already configured via
  `GOOGLE_APPLICATION_CREDENTIALS`), and
- a single Python class in your Django app.

This makes it ideal for serverless Django applications on Cloud Run, where you want powerful
orchestration without operational overhead.
