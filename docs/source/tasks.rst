.. _tasks:

Tasks
=====

In django, tasks are used to handle processing work that happens outside of the main request-response cycle.

`django-gcp` allows tasks to be processed in a serverless environment like cloud run, triggered by
managed services like Cloud Tasks, Cloud Scheduler or Pub/Sub topics.


.. toctree::
   :maxdepth: 1

   tasks_about
   tasks_usage
   tasks_settings
   tasks_workers
