# Disables for testing:
# pylint: disable=missing-docstring
# pylint: disable=protected-access

import json
import logging
from unittest import mock

from django.test import RequestFactory, SimpleTestCase
from google.cloud.logging_v2.handlers.middleware.request import _thread_locals as request_thread_locals

from django_gcp.logs import GoogleStructuredLogsHandler


def make_record(msg, args=None, pathname="/django/core/servers/basehttp.py", **extra):
    """Build a LogRecord as the django.server logger would (module is derived from pathname)"""
    record = logging.LogRecord(
        name="django.server",
        level=logging.INFO,
        pathname=pathname,
        lineno=1,
        msg=msg,
        args=args,
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def make_socket(peer=("192.0.2.1", 51234)):
    """Mock the client socket that django.server attaches as the record's `request`"""
    sock = mock.MagicMock(spec=["getpeername"])
    sock.getpeername.return_value = peer
    return sock


class TestGoogleStructuredLogsHandler(SimpleTestCase):
    """Tests for the httpRequest enrichment of structured logs
    (https://github.com/octue/django-gcp/issues/25)
    """

    def setUp(self):
        self.handler = GoogleStructuredLogsHandler(stream=mock.MagicMock())
        # Google's RequestMiddleware (installed in the example server settings) stores each
        # request in a thread local which outlives the request; clear it so records in
        # these tests don't pick up request context leaked from other test modules
        request_thread_locals.request = None

    def format_record(self, record):
        """Run the handler's filters then format, as logging does during handle()"""
        for log_filter in self.handler.filters:
            log_filter.filter(record)
        return json.loads(self.handler.format(record))

    def test_django_server_record_enriches_http_request(self):
        record = make_record(
            '"%s" %s %s',
            args=("GET /path/to/page?q=1 HTTP/1.1", "200", "1234"),
            status_code=200,
            request=make_socket(),
        )
        payload = self.format_record(record)
        self.assertEqual(
            payload["httpRequest"],
            {
                "requestMethod": "GET",
                "requestUrl": "/path/to/page?q=1",
                "protocol": "HTTP/1.1",
                "status": 200,
                "responseSize": "1234",
                "remoteIp": "192.0.2.1",
            },
        )
        # The quotation marks around the request line are removed from the message
        self.assertEqual(payload["message"], "GET /path/to/page?q=1 HTTP/1.1 200 1234")

    def test_django_server_https_on_http_record_does_not_crash(self):
        """The dev server logs an argument-less message with status 500 when accessed
        over HTTPS; previously this crashed the formatter with an IndexError
        """
        record = make_record(
            "You're accessing the development server over HTTPS, but it only supports HTTP.",
            args=(),
            status_code=500,
            request=make_socket(),
        )
        payload = self.format_record(record)
        self.assertEqual(payload["httpRequest"]["status"], 500)

    def test_basehttp_record_without_status_code_does_not_crash(self):
        """basehttp can emit records with no status_code attribute; previously this
        crashed the formatter with an AttributeError
        """
        record = make_record("Broken pipe from %s", args=("192.0.2.1",))
        payload = self.format_record(record)
        self.assertEqual(payload["message"], "Broken pipe from 192.0.2.1")

    def test_disconnected_socket_is_tolerated(self):
        sock = make_socket()
        sock.getpeername.side_effect = OSError("disconnected")
        record = make_record(
            '"%s" %s %s',
            args=("GET / HTTP/1.1", "200", "5"),
            status_code=200,
            request=sock,
        )
        payload = self.format_record(record)
        self.assertNotIn("remoteIp", payload["httpRequest"])
        self.assertEqual(payload["httpRequest"]["requestMethod"], "GET")

    def test_record_with_django_http_request_enriches_http_request(self):
        """Records carrying a Django HttpRequest (as django.request emits for 4xx/5xx
        responses) get full request information
        """
        request = RequestFactory().get(
            "/missing/page",
            HTTP_USER_AGENT="test-agent/1.0",
            HTTP_REFERER="https://example.com/",
        )
        record = make_record(
            "Not Found: %s",
            args=("/missing/page",),
            pathname="/django/utils/log.py",
            status_code=404,
            request=request,
        )
        payload = self.format_record(record)
        self.assertEqual(
            payload["httpRequest"],
            {
                "requestMethod": "GET",
                "requestUrl": "http://testserver/missing/page",
                "protocol": "HTTP/1.1",
                "remoteIp": "127.0.0.1",
                "userAgent": "test-agent/1.0",
                "referer": "https://example.com/",
                "status": 404,
            },
        )

    def test_plain_record_is_untouched(self):
        record = make_record("A plain message", args=None, pathname="/myapp/views.py")
        payload = self.format_record(record)
        self.assertEqual(payload["httpRequest"], {})
        self.assertEqual(payload["message"], "A plain message")
