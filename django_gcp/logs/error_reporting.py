# Disabled because the handler must capture in the event of all exceptions
# pylint: disable=broad-except

import copy
from logging import StreamHandler
from logging.handlers import QueueListener
import os
import queue
import threading

from django.conf import settings
from google.cloud import error_reporting

PENDING_REPORTS_LIMIT = 1000
SHUTDOWN_SECONDS = 3


class _ContainedListener(QueueListener):
    def __init__(self, pending, send, on_failure):
        super().__init__(pending)
        self._send = send
        self._on_failure = on_failure

    def handle(self, record):
        try:
            self._send(record)
        except Exception:
            self._on_failure(record)

    def stop(self, timeout=None):
        if self._thread is None:
            return
        try:
            self.queue.put(self._sentinel, timeout=timeout)
        except queue.Full:
            pass
        self._thread.join(timeout)
        self._thread = None


class GoogleErrorReportingHandler(StreamHandler):
    """A logging handler which sends logs to Google Cloud Error Reporting from a background thread.

    Set the GCP_ERROR_REPORTING_SERVICE_NAME setting so that GCP Error Reporting allows you to
    filter logs down to those coming from this service.

    The logging thread formats each record and puts it on a bounded queue, then returns without
    waiting for the Error Reporting API. One listener thread per process takes records off the
    queue and sends them. The listener starts when the first record arrives, and a process forked
    from one with a listener starts its own. When ``pending_reports_limit`` records are already
    waiting, further records are not reported and are counted in ``dropped_reports``. A report
    that fails is passed to ``handleError``, counted in ``failed_reports``, and does not stop the
    listener. On ``close()`` the handler waits up to ``shutdown_seconds`` to hand the stop signal
    to the listener and up to ``shutdown_seconds`` again for the listener to finish sending what
    is queued.
    """

    def __init__(self, *args, pending_reports_limit=PENDING_REPORTS_LIMIT, shutdown_seconds=SHUTDOWN_SECONDS, **kwargs):
        try:
            self.custom_handler_client = error_reporting.Client(service=self.error_reporting_service_name)

        except Exception as exp:
            print(
                "GoogleErrorReportingHandler client not connected, possibly due to invalid or missing google application credentials. Error was:"
            )
            print(exp)
            print("Skipping initialisation of Error Reporting handler.")
            self.custom_handler_client = None
        super().__init__(*args, **kwargs)
        self.pending_reports_limit = pending_reports_limit
        self.shutdown_seconds = shutdown_seconds
        self.dropped_reports = 0
        self.failed_reports = 0
        self.listener = None
        self._pending = None
        self._listener_process_id = None
        self._listener_lock = threading.Lock()

    def emit(self, record):
        if self.custom_handler_client is None:
            return

        try:
            self._dispatch(self._formatted_copy(record))

        except queue.Full:
            self.dropped_reports += 1

        # Avoid exception logging on keyboard error or system exit
        # pylint: disable-next=try-except-raise
        except (KeyboardInterrupt, SystemExit):
            raise

        except Exception:
            self.handleError(record)

    def close(self):
        with self._listener_lock:
            if self.listener is not None and self._listener_process_id == os.getpid():
                self.listener.stop(self.shutdown_seconds)
            self.listener = None
            self._listener_process_id = None
        super().close()

    @property
    def error_reporting_service_name(self):
        """The name of this service, as visible in GCP error reporting

        This is determined from the GCP_ERROR_REPORTING_SERVICE_NAME setting. If
        you're running in GCP Cloud Run, then it's recommended to use `env.HOSTNAME`
        to set this value.

        """
        return getattr(settings, "GCP_ERROR_REPORTING_SERVICE_NAME")

    def _dispatch(self, report):
        self._listen_in_this_process()
        self._pending.put_nowait(report)

    def _send(self, report):
        self.custom_handler_client.report(report.msg)

    def _formatted_copy(self, record):
        message = self.format(record)
        report = copy.copy(record)
        report.message = message
        report.msg = message
        report.args = None
        report.exc_info = None
        report.exc_text = None
        report.stack_info = None
        return report

    def _listen_in_this_process(self):
        if self._listener_process_id == os.getpid():
            return
        with self._listener_lock:
            if self._listener_process_id == os.getpid():
                return
            self._pending = queue.Queue(maxsize=self.pending_reports_limit)
            self.listener = _ContainedListener(self._pending, self._send, self._report_failed)
            self.listener.start()
            self._listener_process_id = os.getpid()

    def _report_failed(self, report):
        self.failed_reports += 1
        self.handleError(report)


class ForegroundGoogleErrorReportingHandler(GoogleErrorReportingHandler):
    """A GoogleErrorReportingHandler which sends each report from the thread that logged it."""

    def _dispatch(self, report):
        self._send(report)
