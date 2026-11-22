# Disabled because the handler must capture in the event of all exceptions
# pylint: disable=broad-except

from logging import StreamHandler

from django.conf import settings
from google.cloud import error_reporting


class GoogleErrorReportingHandler(StreamHandler):
    """A logging handler which streams logs to google cloud error handling.
    Set the GCP_ERROR_REPORTING_SERVICE_NAME environment variable so that GCP Error Reporting allows
    you to filter logs down to those coming from to this service.
    """

    def __init__(self, *args, **kwargs):
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

    def emit(self, record):
        if self.custom_handler_client is None:
            return

        try:
            # Apply any formatters
            msg = self.format(record)

            # Send report to GCP Error Reporting
            self.custom_handler_client.report(msg)

        # Avoid exception logging on keyboard error or system exit
        # pylint: disable-next=try-except-raise
        except (KeyboardInterrupt, SystemExit):
            raise

        except Exception:
            self.handleError(record)

    @property
    def error_reporting_service_name(self):
        """The name of this service, as visible in GCP error reporting

        This is determined from the GCP_ERROR_REPORTING_SERVICE_NAME setting. If
        you're running in GCP Cloud Run, then it's recommended to use `env.HOSTNAME`
        to set this value.

        """
        return getattr(settings, "GCP_ERROR_REPORTING_SERVICE_NAME")
