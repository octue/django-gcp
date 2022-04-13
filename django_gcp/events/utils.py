import logging
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlencode


logger = logging.getLogger(__name__)


def get_event_url(event_kind, event_reference, event_parameters=None, url_namespace="gcp-events", base_url=None):
    """Returns a fully constructed url for the events endpoint, suitable for receipt and processing of events
    :param str event_kind: The kind of the event (must be url-safe)
    :param str event_reference: A reference allowing either identification of unique events or a group of related events (must be url-safe)
    :param Union[dict, None] event_parameters: Dict of additional parameters to encode into the URL querystring, for example use {"token": "abc"} to add a token parameter that gets received by the endpoint.
    :param str url_namespace: Default 'gcp-events'. URL namespace of the django-gcp events (see https://docs.djangoproject.com/en/4.0/topics/http/urls/#url-namespaces)
    :param Union[str, None] base_url: The base url (eg https://somewhere.com) for the URL. By default, this uses django's BASE_URL setting. To generate an empty value (a relative URL) use an empty string ''.
    :return str: The fully constructed webhook endpoint
    """
    url = reverse(url_namespace, args=[event_kind, event_reference])
    if event_parameters is not None:
        url = url + "?" + urlencode(event_parameters)

    if base_url is None:
        try:
            base_url = settings.BASE_URL
        except AttributeError as e:
            raise AttributeError(
                "Either specify BASE_URL in your settings module, or explicitly pass a base_url parameter to get_push_endpoint()"
            ) from e

    url = base_url + url

    logger.debug("Generated webhook endpoitn url %s", url)

    return url
