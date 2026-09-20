# Logs

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
Django-specific behaviour to the Google `StructuredLogHandler` used under the hood. It
enriches the
[`httpRequest` field](https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry#HttpRequest)
of a log entry where the record carries request information:

- Entries from the `django.server` logger (the development server's request log) gain the
  request method, URL, protocol, status, response size and remote IP. The URL for these
  entries is the request path rather than an absolute URL, because that is all the
  development server records.
- Entries whose record carries a Django `HttpRequest` — as the `django.request` logger
  attaches for 4xx and 5xx responses — gain the request method, URL, protocol, remote IP,
  user agent, referer and status.

## Request context and trace correlation

Google's logging library can attach request and trace information to **every** log entry
emitted while handling a request, not only the request log entries described above. To
enable this, add Google's `RequestMiddleware` to your `MIDDLEWARE` setting:

```python
MIDDLEWARE = [
    "google.cloud.logging_v2.handlers.middleware.RequestMiddleware",
    # ... your other middleware ...
]
```

With the middleware installed, each entry logged during a request infers `httpRequest`
data (method, URL, user agent and protocol) from that request. Trace context is read from
the `traceparent` or `X-Cloud-Trace-Context` request headers — which Cloud Run and Cloud
Load Balancing set automatically — and populates the entry's `trace`, `spanId` and
`traceSampled` fields, so all entries for one request can be grouped and filtered together
in the Logs Explorer.

## Error Reporting

This is not the same thing as structured logging.

If you use Google Cloud Error Reporting (as opposed to Sentry or similar), `django-gcp`
provides a handler enabling you to send errors and exceptions directly from Django. You can
then configure Error Reporting as you wish — for example to track unresolved errors, email
teams, or connect issue trackers.

`django-gcp` provides `django_gcp.logs.GoogleErrorReportingHandler` to do this. You need to
set the `GCP_ERROR_REPORTING_SERVICE_NAME` value in your `settings.py`.
