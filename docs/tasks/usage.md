# Creating and using tasks

## Creating tasks

A task is created by subclassing one of the `OnDemandTask`, `PeriodicTask`, or `SubscriberTask`
classes. In each task, the `run` method must be overridden and any relevant class variables
set. See the
[full example implementation](https://github.com/octue/django-gcp/tree/main/tests/server) for
example tasks of each kind.

## Registering tasks

For tasks to be registered, they must be imported in the app's `AppConfig.ready` method. For
example, if the classes are defined in modules in a subpackage of the app called `tasks`, the
app config would look like this:

```python
class ExampleAppConfig(AppConfig):
    """Example (test server) app showing how you would use django-gcp within your own django server"""

    # ...

    def ready(self):
        # Import the tasks only once the app is ready, in order to register them.
        from . import tasks
```

Note that this requires the task classes to be imported in `tasks/__init__.py`.

## Creating resources with the `task_manager` command

Periodic tasks are triggered by cron jobs in Google Cloud Scheduler, and subscriber tasks are
triggered by Pub/Sub messages arriving at subscriptions. Neither of these resources is created
implicitly: you may wish to manage them directly with Terraform, or you can create them from
your registered task classes using the `task_manager` management command.

The command takes one or more actions — `create_scheduler_jobs` and
`create_pubsub_subscriptions` — and supports two options:

- `--tasks-domain` overrides the `GCP_TASKS_DOMAIN` setting, so you can direct the created
  resources at a specific worker domain.
- `--cleanup` removes unused resources whose names are affixed with
  `GCP_TASKS_RESOURCE_AFFIX` (see [Settings](settings.md)).

### Scheduling periodic tasks

To create or update the Cloud Scheduler jobs for your `PeriodicTask` classes:

```bash
python manage.py task_manager create_scheduler_jobs
```

!!! warning

    To create scheduler jobs, your service account needs the `cloudscheduler.update`
    permission. Here is how to apply that to a service account using Terraform:

    ```hcl
    # Allow django-gcp tasks to create periodic tasks in google cloud scheduler
    resource "google_project_iam_binding" "cloudscheduler_admin" {
      project = var.project
      role    = "roles/cloudscheduler.admin"
      members = [
        "serviceAccount:your-service-account@your-project.iam.gserviceaccount.com",
      ]
    }
    ```

### Setting up subscriber tasks

To create the Pub/Sub subscriptions for your `SubscriberTask` classes:

```bash
python manage.py task_manager create_pubsub_subscriptions
```

## Enqueuing on-demand tasks

`OnDemandTask` subclasses are enqueued from your code with their `enqueue()` method (or
`enqueue_later()` to schedule execution for a future time). The payload you pass is delivered
to the task's `run` method by Cloud Tasks via your worker's endpoint.

### Deduplicating tasks

`OnDemandTask` subclasses with the attribute `deduplicate = True` have the special property
that the task cannot be repeated. Deduplication uses both the task name **and** a `short_sha`
of the payload data. That is:

- You can enqueue the same task twice in succession with different payloads.
- If you enqueue the same task with the same payload twice in quick succession, you get a
  `DuplicateTaskError`.
- A duplicate task will fail for around one hour after it is either executed or deleted from
  the queue.

!!! tip

    Deduplicating tasks introduces significant additional latency into the task queue, so do
    not enable it unless you have to.

!!! note

    GCP requires a task ID to deduplicate tasks, and for optimal queue performance the string
    ordering of task IDs should be approximately binomially distributed. `django-gcp` prefixes
    the `short_sha` of the payload to ensure this (as opposed to prefixing the task name, which
    would give a highly non-optimal distribution in N clusters, where N is the number of
    differently-named tasks).

## More information

Have a look at the management commands available, both in `django-gcp` and the
[example app](https://github.com/octue/django-gcp/tree/main/tests/server). If you are having
problems, get in touch by raising an issue on GitHub and we will help you configure your app.
