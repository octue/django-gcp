.. _about_tasks:

About tasks in django
=====================

Tasks in django include, for example, dispatching jobs whose execution is too long to occur within a request
(anything more than a few hundred milliseconds should probably be offloaded), running scheduled
maintenance tasks (like refreshing a cache), or processing data that doesn't need to be done within a request
loop.

The classic example is sending email to a user responding to a registration request: a task requiring
interaction with a third party API, making the request slow.

Existing solutions
------------------

Historically, to manage the queue of tasks django has required the use of libraries like `celery` (which is
very tricky to set up correctly) or `django-dramatiq` (a much cleaner API than Celery, still a great option
today) with an external message handler/store like REDIS.

However, managing these queues requires the dev team to think about exactly-once delivery, retries and throttling.
A redis or rabbitmq instance must be created and managed. To invoke tasks periodically, a cron job is required
(meaning yet another working part somewhere in the devops maze). Finally, these systems operate on a **pull-based**
model, meaning that you constantly have to have workers alive, listening to the queue.

All that makes it difficult to run django in a serverless environment like Cloud Run. Plus, where tasks are only
intermittent, it wastes a lot of money having workers up all the time.

Why ``django-gcp`` for tasks?
-----------------------------

`django-gcp` uses a **push-based** model, meaning that workers can be *serverless*:
autoscaled from zero in response to task requests.

It uses Google's managed services,
`Cloud Tasks <https://cloud.google.com/tasks>`_ and `Cloud Scheduler <https://cloud.google.com/scheduler>`_
enabling very quick and easy configuration of robust task queues and periodic triggers.
