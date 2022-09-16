.. _tasks_usage:

Creating and using tasks
========================

TODO: I've written SO MUCH already and need to get this into production. This week.

I'll come back and explain this, I promise.

~~ Tom ~~

IN THE MEANTIME:

Look at management commands available (both in django gcp and the example app), and look at the `full example implementation here <https://github.com/octue/django-gcp/tree/main/tests/server>`_ to pick up how to define and use tasks :)

If you need to use this library and can't figure it out, get in touch by raising an issue on GitHub and we'll help you configure your app (and write the docs at the same time).


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
