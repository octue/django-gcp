.. ATTENTION::
    The log handlers included here work great but we suspect some improvements could be made
    to the structure of the logs to give fuller / more easily filterable results, especially
    around ``trace``/``span`` and the contents of the ``httpRequest`` object. `Pick up the issue here: PRs are welcome! <https://github.com/octue/django-gcp/issues/25>`_


.. _logs:

====
Logs
====

.. tip::
   Quickly set up logging out of the box, by dropping the `LOGGING entry from the example test server <https://github.com/octue/django-gcp/blob/main/tests/server/settings.py>`_
   into your ``settings.py``.


.. _structured_logging:

Structured logs
===============

On Google Cloud, if you use `structured logging <https://cloud.google.com/logging/docs/structured-logging>`_, your entries can be filtered and
inspected much more powerfully than if you log in plain text.

Django has its own `default logging configuration <https://docs.djangoproject.com/en/4.1/ref/logging/#default-logging-configuration>`_, and we need to do some
tweaking to it to make sure we capture the information in a structured way. Notice particularly that the ``django`` and ``django.server`` modules have specific setups to record,
for example, request-level information.

``django-gcp`` provides :class:`django_gcp.logs.GoogleStructuredLogsHandler` to add django-specific
behaviour to the Google ``StructuredLogsHandler`` that is used under the hood.

.. _error_reporting:

Error Reporting
===============

This isn't the same thing as structured logging.

If you use Google Cloud Error Reporting (as opposed to sentry or similar), ``django-gcp`` provides
a handler enabling you to send errors/exceptions directly from django. Then you can configure Error Reporting
as you wish (eg to track unresolved errors, email teams, connect issue trackers, etc).

``django-gcp`` provides :class:`django_gcp.logs.GoogleErrorReportingHandler` to do this. You need to set the
``GCP_ERROR_REPORTING_SERVICE_NAME`` value in your settings.py.
