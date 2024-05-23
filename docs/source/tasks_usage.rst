.. _tasks_usage:

Creating and using tasks
========================

Creating tasks
--------------
A task is created by subclassing one of the ``OnDemandTask``, ``PeriodicTask``,  or ``SubscriberTask`` classes. In each
task, the ``run`` method must be overridden and any relevant class variables set. See the `full example implementation
here <https://github.com/octue/django-gcp/tree/main/tests/server>`_ to see some example tasks.

Registering tasks
-----------------
For tasks to be registered, they must be imported in the app's ``AppConfig.ready`` method. For example, if the classes
are defined in modules in a subpackage of the app called ``tasks``, the app config would look like this:

.. code-block:: python

    class ExampleAppConfig(AppConfig):
    """Example (test server) app showing how you would use django-gcp within your own django server"""

    ...

    def ready(self):
        # Import the tasks only once the app is ready, in order to register them.
        from . import tasks

Note that this requires the task classes to be imported in ``tasks/__init__.py``.

Scheduling periodic tasks
-------------------------
Periodic tasks are triggered by cronjobs in Google Cloud Scheduler.
To create these resources, you may wish to manage them directly with
terraform but it's possible to create the resources using the ``create_scheduler_jobs``
action from the ``task_manager``` management command:

.. code-block::

    # Note: use the --task-domain flag to override the domain where tasks will get sent
    python manage.py task manager create_scheduler_jobs

.. attention::

   To register these resources, your service account will need to have ``cloudscheduler.update`` permission. Here's how to apply that to a service account using terraform:

   .. code-block::

      # Allow django-gcp tasks to create periodic tasks in google cloud scheduler
      resource "google_project_iam_binding" "cloudscheduler_admin" {
        project = var.project
        role    = "roles/cloudscheduler.admin"
        members = [
          "serviceAccount:your-service-account@your-project.iam.gserviceaccount.com",
        ]
      }

Setting up subscriber tasks
---------------------------
Subscriber tasks are triggered by Pub/Sub messages received by subscriptions. To create these subscriptions, the
``create_pubsub_subscriptions`` management command must be run.

More information
----------------
Have a look at the management commands available (both in ``django-gcp`` and the example app). If you are having
problems, get in touch by raising an issue on GitHub and we'll help you configure your app.

Deduplicating tasks
-------------------

OnDemandTask classes with the attribute `deduplicate = true` have the special property that the task cannot be repeated.

Duplication is done using both the task name AND a `short_sha` of the payload data. That is:

* You can enqueue the same task twice in succession with different payloads.
* If you enqueue the same task with the same payload twice in quick succession, you will get a DuplicateTaskError.
* A duplicate task will fail for ~1 hour after it is either executed or deleted from the queue.

.. tip::
   Deduplicating tasks introduces significant additional latency into the task queue.
   So don't do it unless you have to!

.. note::
   GCP requires a task ID to deduplicate tasks, whose string ordering should be optimally binomaially distributed.
   ``django-gcp`` always prefixes the ``short_sha`` of the payload to ensure that the created task IDs are approximately
   binomially distributed (as opposed to using the task name as a prefix, which would give a highly non-optimal distribution
   in N clusters, where N is the number of differently named tasks).
