.. ATTENTION::
    This library is used for a few apps in production, but it is still early in development.
    Like the idea of it? Please
    `star us on GitHub <https://github.com/octue/django-gcp>`_ and contribute via the
    `issues board <https://github.com/octue/django-gcp/issues>`_ and
    `roadmap <https://github.com/octue/django-gcp/projects/1>`_.

==========
Django GCP
==========

**django-gcp** is a library of tools to help you deploy and use django on Google Cloud Platform.
Integrations provided by ``django-gcp``:

* `Google Cloud Storage <https://cloud.google.com/storage>`_,
* `PubSub and EventArc <https://cloud.google.com/pubsub>`_,
* `Cloud Tasks <https://cloud.google.com/tasks>`_ and
* `Cloud Scheduler <https://cloud.google.com/scheduler>`_.


.. _aims:

Aims
====

The ultimate goals are to:

- **Allow serverless django** (for actual fully-fledged apps, not toybox tutorials).

- **Enable event-based integration** between django and various GCP services.

- **Simplify the use of GCP resources in django** including Storage, PubSub, Tasks and Scheduler.

.. TIP::
    For example, if we have *both* a Store *and* a PubSub subscription to events on that store, we can do smart things in django when files or their metadata change.


Background
----------

To run a "reasonably comprehensive" django server on GCP, we have been using 4-5 libraries.
Each covers a little bit of functionality, and we put in a lot of time to:

.. code-block::

   engage maintainers -> fork -> patch -> PR -> wait -> wait more -> release (maybe) -> update dependencies

Lots of the maintainers of those libraries have given up or are snowed under, which we have a lot of compassion for.
Some, like django-storages, are (admirably) maintaining a uniform API across many compute providers,
whereas we don't change providers often enough to need that, so would rather have the flexibility to do
platform-specific things.

We'll be using GCP for the foreseeable future, so can accept a platform-specific API in order to use latest GCP features and best practices.


Contents
=============

.. toctree::
   :maxdepth: 2

   self
   getting_started
   authentication
   storage
   events
   tasks
   projects
   license
   version_history

Thanks
======

This project is heavily based on a couple of really great libraries, particularly ``django-storages`` and ``django-cloud-tasks``.
See `our attributions page <https://github.com/octue/django-gcp/blob/main/ATTIBUTIONS.md>`_.

Thank you so much to the (many) authors of these libraries :)

Also, this library boilerplate is from the ``django-rabid-armadillo`` project...

.. figure:: images/unhappy_armadillo.jpg
    :width: 150px
    :align: center
    :figclass: align-center
    :alt: Unhappy armadillo
