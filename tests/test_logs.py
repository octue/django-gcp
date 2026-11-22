# Disables for testing:
# pylint: disable=missing-docstring
# pylint: disable=protected-access

import io
import json
import logging
import os
import sys
import threading
from unittest import mock

from django.test import RequestFactory, SimpleTestCase
from google.cloud.logging_v2.handlers.middleware.request import _thread_locals as request_thread_locals

from django_gcp.logs import (
    ForegroundGoogleErrorReportingHandler,
    GoogleErrorReportingHandler,
    GoogleStructuredLogsHandler,
)


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


def make_error_record(message="It broke"):
    return logging.LogRecord("myapp", logging.ERROR, __file__, 1, message, None, None)


class FakeClient:
    def __init__(self):
        self.reported = []
        self.threads = []
        self.started = threading.Event()
        self.may_finish = threading.Event()
        self.may_finish.set()
        self.failures_left = 0

    def report(self, message):
        self.started.set()
        self.may_finish.wait(timeout=10)
        if self.failures_left:
            self.failures_left -= 1
            raise RuntimeError("The report could not be sent")
        self.threads.append(threading.get_ident())
        self.reported.append(message)


class TestGoogleErrorReportingHandler(SimpleTestCase):
    def setUp(self):
        self.client = FakeClient()
        self.handlers = []

    def tearDown(self):
        self.client.may_finish.set()
        for handler in self.handlers:
            handler.close()

    def make_handler(self, handler_class=GoogleErrorReportingHandler, **kwargs):
        with mock.patch("django_gcp.logs.error_reporting.error_reporting.Client", return_value=self.client):
            handler = handler_class(stream=io.StringIO(), **kwargs)
        handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        self.handlers.append(handler)
        return handler

    def test_record_is_reported_with_its_formatted_message(self):
        handler = self.make_handler()

        handler.handle(make_error_record())
        handler.close()

        self.assertEqual(self.client.reported, ["ERROR It broke"])

    def test_records_are_skipped_without_raising_when_the_client_could_not_be_created(self):
        with mock.patch(
            "django_gcp.logs.error_reporting.error_reporting.Client", side_effect=RuntimeError("No credentials")
        ):
            handler = GoogleErrorReportingHandler(stream=io.StringIO())
        self.handlers.append(handler)

        with mock.patch.object(handler, "handleError") as handle_error:
            handler.handle(make_error_record())

        handle_error.assert_not_called()
        self.assertIsNone(handler.listener)

    def test_the_logging_thread_does_not_wait_for_the_report(self):
        self.client.may_finish.clear()
        handler = self.make_handler()

        handler.handle(make_error_record("First"))

        self.assertTrue(self.client.started.wait(timeout=5))
        self.assertEqual(self.client.reported, [])
        self.client.may_finish.set()
        handler.close()
        self.assertEqual(self.client.reported, ["ERROR First"])
        self.assertNotIn(threading.get_ident(), self.client.threads)

    def test_no_listener_runs_until_a_record_arrives(self):
        handler = self.make_handler()
        self.assertIsNone(handler.listener)

        handler.handle(make_error_record())

        self.assertIsNotNone(handler.listener)

    def test_closing_the_handler_sends_the_reports_still_pending(self):
        handler = self.make_handler()
        for number in range(3):
            handler.handle(make_error_record(f"Report {number}"))

        handler.close()

        self.assertEqual(self.client.reported, ["ERROR Report 0", "ERROR Report 1", "ERROR Report 2"])

    def test_closing_does_not_wait_for_a_report_that_does_not_finish(self):
        self.client.may_finish.clear()
        handler = self.make_handler(shutdown_seconds=0.2)
        handler.handle(make_error_record())
        self.assertTrue(self.client.started.wait(timeout=5))

        closer = threading.Thread(target=handler.close)
        closer.start()
        closer.join(timeout=5)

        self.assertFalse(closer.is_alive())

    def test_records_beyond_the_pending_limit_are_counted_and_dropped(self):
        self.client.may_finish.clear()
        handler = self.make_handler(pending_reports_limit=1)
        handler.handle(make_error_record("Being sent"))
        self.assertTrue(self.client.started.wait(timeout=5))

        handler.handle(make_error_record("Waiting"))
        handler.handle(make_error_record("Dropped"))

        self.assertEqual(handler.dropped_reports, 1)
        self.client.may_finish.set()
        handler.close()
        self.assertEqual(self.client.reported, ["ERROR Being sent", "ERROR Waiting"])

    def test_a_failed_report_is_passed_to_handle_error_and_counted_and_later_reports_are_still_sent(self):
        self.client.failures_left = 1
        handler = self.make_handler()

        with mock.patch.object(handler, "handleError") as handle_error:
            handler.handle(make_error_record("Fails"))
            handler.handle(make_error_record("Sent"))
            handler.close()

        self.assertEqual(handler.failed_reports, 1)
        self.assertEqual(handle_error.call_count, 1)
        self.assertEqual(handle_error.call_args.args[0].getMessage(), "ERROR Fails")
        self.assertEqual(self.client.reported, ["ERROR Sent"])

    def test_the_report_carries_the_formatted_traceback_and_no_live_exception(self):
        handler = self.make_handler()
        try:
            raise ValueError("Bad value")
        except ValueError:
            record = logging.LogRecord("myapp", logging.ERROR, __file__, 1, "It broke", None, sys.exc_info())

        handler.handle(record)
        handler.close()

        self.assertIn("ValueError: Bad value", self.client.reported[0])
        self.assertIsNotNone(record.exc_info)

    def test_a_forked_process_starts_its_own_listener(self):
        handler = self.make_handler()
        handler.handle(make_error_record())
        parent_listener = handler.listener

        with mock.patch("django_gcp.logs.error_reporting.os.getpid", return_value=os.getpid() + 1):
            handler.handle(make_error_record())
            child_listener = handler.listener
            handler.close()

        self.assertIsNot(child_listener, parent_listener)
        parent_listener.stop(1)

    def test_the_foreground_handler_reports_in_the_logging_thread_before_returning(self):
        handler = self.make_handler(ForegroundGoogleErrorReportingHandler)

        handler.handle(make_error_record())

        self.assertEqual(self.client.reported, ["ERROR It broke"])
        self.assertEqual(self.client.threads, [threading.get_ident()])
        self.assertIsNone(handler.listener)

    def test_a_failed_foreground_report_is_passed_to_handle_error_and_does_not_raise(self):
        self.client.failures_left = 1
        handler = self.make_handler(ForegroundGoogleErrorReportingHandler)
        record = make_error_record()

        with mock.patch.object(handler, "handleError") as handle_error:
            handler.handle(record)

        handle_error.assert_called_once_with(record)
