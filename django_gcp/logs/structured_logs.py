import json

from google.cloud.logging_v2.handlers import StructuredLogHandler


class GoogleStructuredLogsHandler(StructuredLogHandler):
    """A logging handler which structures logs so they're readable in Cloud Run log tabs

    The StructuredLogHandler from Google is used as a basis but the httpRequest field is
    injected to preserve request context (empty by default otherwise), as per the requirements
    at:
    https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry#HttpRequest

    TODO The httpRequest object could have much richer data than this, which should be accessible
    from `record.request` or by adding more advanced middleware. PRs are welcome.

    """

    def format(self, record):
        """Override the default formatter to inject httpRequest information"""

        # Inject http request status to the python logger for logs from django.server
        if (record.module == "basehttp") and record.status_code is not None:
            request_method, request_url, protocol = record.args[0].split(" ")
            httpRequest = {
                "requestMethod": request_method,
                "requestUrl": request_url,
                "protocol": protocol,
                "status": record.status_code,
            }
            # Without overriding the entire format() method, injecting this protected value
            # is the only way of adding httpRequest data to the formatted output
            # pylint: disable-next=protected-access
            record._http_request_str = json.dumps(httpRequest, ensure_ascii=False, cls=self._json_encoder_cls)
            # Override the django.server default log message to remove the quotation marks
            record.msg = "%s %s %s"

        return super().format(record)
