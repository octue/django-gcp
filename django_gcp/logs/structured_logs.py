import json

from django.http import HttpRequest
from google.cloud.logging_v2.handlers import StructuredLogHandler


class GoogleStructuredLogsHandler(StructuredLogHandler):
    """A logging handler which structures logs so they're readable in Cloud Run log tabs

    The StructuredLogHandler from Google is used as a basis, with the httpRequest field
    (see https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry#HttpRequest)
    enriched where a record carries request information that the base handler cannot infer:

    - Records from ``django.server`` (the development server's request log): the request
      method, URL, protocol, status and response size are parsed from the record, and the
      remote IP is taken from the client socket which that logger attaches to the record.
    - Records carrying a Django ``HttpRequest`` as their ``request`` attribute (as the
      ``django.request`` logger does for 4xx and 5xx responses): the method, URL, protocol,
      remote IP, user agent and referer are extracted from the request.

    Fields inferred by the base handler (for example where Google's ``RequestMiddleware``
    is installed; see the logs documentation) are preserved, with record-specific fields
    taking precedence.
    """

    def format(self, record):
        """Override the default formatter to inject httpRequest information"""
        http_request = self._build_http_request(record)
        if http_request:
            # Merge over anything the base handler's filter has already inferred. Without
            # overriding the entire format() method, injecting this protected value is the
            # only way of adding httpRequest data to the formatted output.
            # pylint: disable-next=protected-access
            inferred = getattr(record, "_http_request", None) or {}
            http_request = {key: value for key, value in {**inferred, **http_request}.items() if value is not None}
            record._http_request = http_request  # pylint: disable=protected-access
            # pylint: disable-next=protected-access
            record._http_request_str = json.dumps(http_request, ensure_ascii=False, cls=self._json_encoder_cls)

        return super().format(record)

    def _build_http_request(self, record):
        """Build a LogEntry httpRequest dict from information carried by the record

        Returns an empty dict where the record carries no request information.
        """
        request = getattr(record, "request", None)

        if isinstance(request, HttpRequest):
            http_request = self._from_django_request(request)
        elif record.module == "basehttp":
            http_request = self._from_server_record(record)
        else:
            return {}

        status_code = getattr(record, "status_code", None)
        if status_code is not None:
            http_request["status"] = status_code

        return {key: value for key, value in http_request.items() if value is not None}

    @staticmethod
    def _from_django_request(request):
        """Extract httpRequest fields from a Django HttpRequest (django.request records)"""
        try:
            request_url = request.build_absolute_uri()
        except Exception:  # pylint: disable=broad-except
            # Django raises DisallowedHost for a malformed HTTP_HOST header
            request_url = None

        return {
            "requestMethod": request.method,
            "requestUrl": request_url,
            "protocol": request.META.get("SERVER_PROTOCOL"),
            "remoteIp": request.META.get("REMOTE_ADDR"),
            "userAgent": request.META.get("HTTP_USER_AGENT"),
            "referer": request.META.get("HTTP_REFERER"),
        }

    @staticmethod
    def _from_server_record(record):
        """Extract httpRequest fields from a django.server record

        These records carry the request line, status and response size as message
        arguments, and the client socket as their ``request`` attribute.
        """
        http_request = {}

        args = record.args or ()
        if len(args) == 3:
            request_line, _, response_size = (str(arg) for arg in args)

            parts = request_line.split()
            if len(parts) >= 3:
                http_request["requestMethod"] = parts[0]
                http_request["requestUrl"] = " ".join(parts[1:-1])
                http_request["protocol"] = parts[-1]
                # Remove the quotation marks around the request line in the default
                # django.server message, which garble the structured output. The record
                # is shared with any other handlers on the logger, which will also see
                # the unquoted message; that is accepted as this handler targets
                # deployments where it is the only formatter of these records.
                if isinstance(record.msg, str):
                    record.msg = record.msg.replace('"%s"', "%s")

            if response_size.isdigit():
                # LogEntry represents int64 fields as strings
                http_request["responseSize"] = response_size

        # django.server attaches the client socket as the record's request; the peer
        # is unavailable if the client has already disconnected
        sock = getattr(record, "request", None)
        if hasattr(sock, "getpeername"):
            try:
                peer = sock.getpeername()
                http_request["remoteIp"] = peer[0] if isinstance(peer, (tuple, list)) else str(peer)
            except OSError:
                pass

        return http_request
