# Logs

!!! note

    The log handlers included here work well, but we suspect improvements could be made to the
    structure of the logs to give fuller, more easily filterable results, especially around
    `trace`/`span` and the contents of the `httpRequest` object.
    [Pick up the issue here — PRs are welcome!](https://github.com/octue/django-gcp/issues/25)

!!! tip

    Quickly set up logging out of the box by dropping the
    [`LOGGING` entry from the example test server](https://github.com/octue/django-gcp/blob/main/tests/server/settings.py)
    into your `settings.py`.

## Structured logs

On Google Cloud, if you use
[structured logging](https://cloud.google.com/logging/docs/structured-logging), your entries
can be filtered and inspected much more powerfully than if you log in plain text.

Django has its own
[default logging configuration](https://docs.djangoproject.com/en/stable/ref/logging/#default-logging-configuration),
and some tweaking is needed to make sure the information is captured in a structured way.
Notice particularly that the `django` and `django.server` modules have specific setups to
record, for example, request-level information.

`django-gcp` provides `django_gcp.logs.GoogleStructuredLogsHandler`, which adds
Django-specific behaviour to the Google `StructuredLogsHandler` used under the hood.

## Error Reporting

This is not the same thing as structured logging.

If you use Google Cloud Error Reporting (as opposed to Sentry or similar), `django-gcp`
provides a handler enabling you to send errors and exceptions directly from Django. You can
then configure Error Reporting as you wish — for example to track unresolved errors, email
teams, or connect issue trackers.

`django-gcp` provides `django_gcp.logs.GoogleErrorReportingHandler` to do this. You need to
set the `GCP_ERROR_REPORTING_SERVICE_NAME` value in your `settings.py`.
