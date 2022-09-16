.. _tasks_settings:

Tasks Settings
==============

There are a number of settings required to enable On-Demand and Scheduled tasks to work, we recommend you go through the following
one-by-one...


**In order of importance!**


``GCP_TASKS_DEFAULT_QUEUE_NAME``
--------------------------------
Type: ``string`` (required)

The name of the task queue on GCP used for on-demand tasks. This will be created (if not already present) when you
enqueue your first task.

.. _gcp_tasks_domain:

``GCP_TASKS_DOMAIN``
--------------------
Type: ``string`` (required)

The base url of the server to which tasks will be pushed. In production, this'll need to be set to the URL of your
worker service (see :ref:`deploying_workers`).

.. TIP::
    In local development, set up `localtunnel <https://github.com/localtunnel/localtunnel>`_ and use its `-s` option to set
    yourself an amusing subdomain. You can then set ``GCP_TASKS_DOMAIN = "https://king-julian-in-da-house.loca.lt"`` in your
    local environment, and receive ``https://`` traffic.

    That's awesome, because (assuming you've installed local credentials per :ref:`authenticating_locally` it allows you
    to spin up actual real queues and schedules on GCP to get a feel for how this all works.


``GCP_TASKS_RESOURCE_AFFIX``
----------------------------
Type: ``string``

Default: None

This is a label which is affixed to the names of all resources created by ``django_gcp``. It's HIGHLY RECOMMENDED that you
set this to avoid confusion about what resources belong to what applications, and to enable cleanup of old resources.

If left unset, there'll be no affix applied. This might be exactly what you want, for example if you manage all your
task queues and scheduler jobs on existing infrastructure or using terraform, your own naming convention may already apply.

.. WARNING::
    Without setting ``GCP_TASKS_RESOURCE_AFFIX``, ``django-gcp`` won't be able to clean up after itself so
    you'll have to remove any resources manually yourself.

    Make sure you don't have multiple independent django apps with the same affix, or one app may delete resources for another.

.. NOTE::
    ``SubscriberTask`` subclasses that listen to a PubSub topic don't automatically add a prefix to the topic name they listen to.
    This allows you to subscribe to any topic on GCP for triggering tasks; if you want to use the prefix you can do so when
    defining the ``topic_name`` override


``GCP_TASKS_REGION``
--------------------
Type: ``string``

Default: "europe-west1"

The region in which resources (Task Queues, Scheduler Jobs, and PubSub topics) are accessed and/or created.


``GCP_TASKS_DELIMITER``
-----------------------
Type: ``string``

Default: "--"

The delimiter used when creating resource names with an affix or other identifier.


``GCP_TASKS_EAGER_EXECUTE``
---------------------------
Type: ``boolean``

Default: ``False``

If set to true, tasks will synchronously execute when their ``enqueue()`` method ``is called (eg within a request).

Whilst not generally useful in production, this can be quite helpful for straightforward
debugging of tasks in local environments.
