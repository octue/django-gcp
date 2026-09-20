# About tasks in Django

In Django, tasks are used to handle processing work that happens outside of the main
request-response cycle. `django-gcp` allows tasks to be processed in a serverless environment
like Cloud Run, triggered by managed services like Cloud Tasks, Cloud Scheduler, or Pub/Sub
topics.

Tasks include, for example, dispatching jobs whose execution is too long to occur within a
request (anything more than a few hundred milliseconds should probably be offloaded), running
scheduled maintenance tasks (like refreshing a cache), or processing data that does not need to
be handled within a request loop. The classic example is sending an email in response to a
registration request: a task requiring interaction with a third-party API, which makes the
request slow.

## Existing solutions

Historically, managing a queue of tasks in Django has required libraries like `celery` (which
is very tricky to set up correctly) or `django-dramatiq` (a much cleaner API than Celery, and
still a great option today) with an external message handler or store like Redis.

However, managing these queues requires the team to think about exactly-once delivery, retries,
and throttling. A Redis or RabbitMQ instance must be created and managed. To invoke tasks
periodically, a cron job is required — yet another moving part somewhere in the DevOps maze.
Finally, these systems operate on a **pull-based** model, meaning workers must be constantly
alive, listening to the queue.

All of that makes it difficult to run Django in a serverless environment like Cloud Run, and
where tasks are only intermittent, it wastes a lot of money keeping workers up all the time.

## Why `django-gcp` for tasks?

`django-gcp` uses a **push-based** model, meaning that workers can be _serverless_: autoscaled
from zero in response to task requests.

It uses Google's managed services, [Cloud Tasks](https://cloud.google.com/tasks) and
[Cloud Scheduler](https://cloud.google.com/scheduler), enabling very quick and easy
configuration of robust task queues and periodic triggers.

Read on:

- [Creating and using tasks](usage.md)
- [Settings](settings.md)
- [Deploying workers](workers.md)

!!! warning

    Task endpoints do not authenticate their callers out of the box. Please read
    [Authenticating events and tasks](../authentication/events-and-tasks.md) before exposing
    them.
