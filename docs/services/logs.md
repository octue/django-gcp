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

## Attach handlers to the root logger only

Python passes a log record to the handlers of the logger that created it, then to the handlers
of each ancestor logger for as long as each logger's `propagate` attribute is true. A handler
attached both to the root logger and to a named logger such as `django` therefore receives
every record from `django.request` twice: it writes two structured log entries and sends two
Error Reporting events for one error.

Attach the handlers to the root logger only, and use the `loggers` section of `LOGGING` to set
each named logger's level and `propagate`, without handlers. Set `propagate` explicitly on the
loggers you list, because Django's
[default configuration](https://docs.djangoproject.com/en/stable/ref/logging/#default-logging-configuration)
turns propagation off for `django.server`, and its records would otherwise never reach the root
logger's handlers:

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "root": {"handlers": ["console", "gcp_structured_logging", "gcp_error_reporting"]},
    # ... formatters, filters and handlers as in the example server ...
    "loggers": {
        "django": {"level": "INFO", "propagate": True},
        "django.server": {"level": "INFO", "propagate": True},
    },
}
```

The example server's `require_debug_true` and `require_debug_false` filters select between
the plain console output used in development and the structured and Error Reporting output
used when `DEBUG` is false, so each record is still written once in either mode.

Any library that adds its own handler to the root logger when it is imported, after Django has
applied `LOGGING`, adds a further copy of every record. If you see each entry twice in Cloud
Logging, list the root logger's handlers once your application has started
(`logging.getLogger().handlers`) to find the extra one.

## Error Reporting

This is not the same thing as structured logging.

If you use Google Cloud Error Reporting (as opposed to Sentry or similar), `django-gcp`
provides a handler enabling you to send errors and exceptions directly from Django. You can
then configure Error Reporting as you wish — for example to track unresolved errors, email
teams, or connect issue trackers.

`django-gcp` provides `django_gcp.logs.GoogleErrorReportingHandler` to do this. You need to
set the `GCP_ERROR_REPORTING_SERVICE_NAME` value in your `settings.py`, which names the
service in Error Reporting.

```python
"handlers": {
    "gcp_error_reporting": {
        "level": "ERROR",
        "filters": ["require_debug_false"],
        "class": "django_gcp.logs.GoogleErrorReportingHandler",
        "formatter": "verbose",
    },
},
```

### Reports are sent from a background thread

The handler does not make the Error Reporting API call in the thread that logged the record.
That thread formats the record, including any traceback, puts it on a queue and returns. One
listener thread in each process takes records off the queue and sends them. Logging an error
therefore costs about what logging an INFO record costs, and threads that log errors at the
same time do not wait for each other's reports.

The handler accepts two optional arguments, which you can set as keys of its entry in
`LOGGING`:

- `pending_reports_limit` (integer, default `1000`) is the number of records that may wait in
  the queue. When the queue is full, further records are not reported, and the handler's
  `dropped_reports` attribute counts them.
- `shutdown_seconds` (number, default `3`) is how long `close()` waits to hand the stop signal
  to the listener, and then how long it waits again for the listener to send the reports still
  queued. Python calls `close()` on every handler when the process exits.

The listener starts when the first record reaches the handler, so a process that never logs an
error never starts the thread. A process forked from one that already has a listener, such as a
gunicorn worker forked after the application was preloaded, starts its own.

A report can be lost when more than `pending_reports_limit` records are waiting, when a report
is still unsent when the shutdown wait ends, or when the process is killed. If you also attach
`GoogleStructuredLogsHandler`, it writes its entry in the logging thread, so the error is in
Cloud Logging in each of these cases.

On Cloud Run with CPU throttling enabled (the default for request-based billing), an instance
has processor time only while it is handling a request. A report queued by the last request
before an idle period is sent when the instance next handles a request, or during the shutdown
grace period.

If the handler cannot create its Error Reporting client at start-up, for example because no
credentials are available, it prints the reason and then ignores the records it receives. If a
report fails, the handler passes the failure to `logging.Handler.handleError`, which by default
prints the traceback to standard error, counts it in `failed_reports`, and does not raise into
the code that logged the record.

### Sending reports from the logging thread

`django_gcp.logs.ForegroundGoogleErrorReportingHandler` sends each report from the thread that
logged the record, and returns when the Error Reporting API has answered. Use it where losing a
report is less acceptable than delaying the code that logged it, for example in a short
management command. Each report took about 170 to 240 ms when measured from a Cloud Run
service, and Python holds a handler's lock while the handler sends a record, so in a threaded
server other threads that log an error wait until the report in progress has been sent.
