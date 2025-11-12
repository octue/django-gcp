.. _about_workflows:

About Cloud Workflows
=====================

Google Cloud Workflows is a fully managed orchestration platform that executes services and APIs
in a defined order to accomplish a specific goal. Workflows are particularly useful for coordinating
multi-step processes, handling complex business logic, and integrating multiple cloud services.

What are Workflows?
-------------------

A workflow is a series of steps (written in YAML or JSON) that define your business process. Each step
can call an API, invoke a Cloud Function, query a database, or perform computations. Workflows support:

- **Conditional logic**: Branch based on data or results
- **Loops and iterations**: Process lists or retry operations
- **Error handling**: Catch and handle failures gracefully
- **Sub-workflows**: Compose reusable workflow components
- **Long-running operations**: Execute for up to 1 year

Workflows vs Tasks
------------------

While both workflows and tasks (Cloud Tasks) are used for asynchronous operations, they serve different purposes:

**Cloud Tasks** (via ``OnDemandTask`` in django-gcp):
  - Single HTTP request to an endpoint
  - Stateless execution
  - Best for: Individual background jobs, API calls, simple task queuing
  - Duration: Up to 30 minutes

**Cloud Workflows** (via ``Workflow`` in django-gcp):
  - Multi-step orchestration with state management
  - Complex control flow (conditionals, loops, error handling)
  - Best for: Multi-service coordination, complex business processes, long-running orchestrations
  - Duration: Up to 1 year

**When to use Cloud Workflows:**

- Coordinating multiple API calls across services
- Implementing complex business processes with branching logic
- Building approval workflows or human-in-the-loop processes
- Orchestrating data pipelines with dependencies
- Handling long-running batch operations
- Implementing saga patterns for distributed transactions

**When to use Cloud Tasks:**

- Queueing individual background jobs
- Rate-limiting API calls
- Distributing work across instances
- Simple fire-and-forget operations
- Task scheduling with retries

Why ``django-gcp`` for workflows?
----------------------------------

The ``django-gcp.workflows`` module provides:

1. **Simple Django Integration**: Define workflows as Python classes similar to tasks
2. **Type-safe Arguments**: Automatic JSON serialization using Django's serializers
3. **Execution Tracking**: Get execution IDs for monitoring and status checks
4. **Console URLs**: Easy access to GCP Console for detailed execution views
5. **Infrastructure as Code**: Workflows defined in Terraform, invoked from Django
6. **Consistent API**: Follows the same patterns as other django-gcp modules

No Complex Setup Required
--------------------------

Unlike traditional workflow engines (Airflow, Temporal, etc.) that require:

- Self-hosted infrastructure
- Database setup
- Worker management
- Complex deployment pipelines

Cloud Workflows (via django-gcp) only requires:

- Workflow definition in your Terraform/infrastructure code
- Service account with workflow execution permissions (already set via ``GOOGLE_APPLICATION_CREDENTIALS``)
- A single Python class in your Django app

This makes it ideal for serverless Django applications on Cloud Run where you want powerful
orchestration without operational overhead.
