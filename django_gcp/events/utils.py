import base64
import json
import logging
from datetime import timezone
from dateutil.parser import isoparse
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlencode


logger = logging.getLogger(__name__)


def _make_naive_utc(value):
    """Converts a timezone-aware datetime.datetime to UTC then makes it naive.
    Used for strictly formatting the UTC-in-nanoseconds publish time of pub/sub messages
    """
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


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


def make_pubsub_message(
    data,
    attributes=None,
    message_id=None,
    ordering_key=None,
    publish_time=None,
):
    """Make a json-encodable message replicating the GCP Pub/Sub v1 format

    For more details see: https://cloud.google.com/pubsub/docs/reference/rest/v1/PubsubMessage

    :param Union[dict, list] data: JSON-serialisable data to form the body of the message
    :param Union[dict, None] attributes: Dict of attributes to attach to the message. Contents must be flat, containing only string keys with string values.
    :param Union[str, None] message_id: An optional id for the message.
    :param Union[str, None] ordering_key: A string used to order messages.
    :param Union[datetime, None] publish_time: If sending a message to PubSub, this will be set by the server on receipt so generally should be left as `None`. However, for the purposes of mocking messages for testing, supply a python datetime specifying the publish time of the message, which will be converted to a string timestamp with nanosecond accuracy.
    :return dict: A dict containing a fully composed PubSub message

    """
    out = dict()

    out["data"] = base64.b64encode(json.dumps(data).encode()).decode()

    if publish_time is not None:
        publish_time_utc_naive = _make_naive_utc(publish_time)
        iso_us = publish_time_utc_naive.isoformat()
        iso_ns = f"{iso_us}000Z"
        out["publishTime"] = iso_ns

    if attributes is not None:
        # Check all attributes are k-v pairs of strings
        for k, v in attributes.items():
            if k.__class__ != str:
                raise ValueError("All attribute keys must be strings")
            if v.__class__ != str:
                raise ValueError("All attribute values must be strings")
        out["attributes"] = attributes

    if message_id is not None:
        if message_id.__class__ != str:
            raise ValueError("The message_id, if given, must be a string")
        out["messageId"] = message_id

    if ordering_key is not None:
        if ordering_key.__class__ != str:
            raise ValueError("The ordering_key, if given, must be a string")
        out["orderingKey"] = ordering_key

    return out


def decode_pubsub_message(message):
    """Decode data within a pubsub message
    :parameter dict message: The Pub/Sub message, which should already be decoded from a raw JSON string to a dict.
    :return: None
    """

    decoded = {
        "data": json.loads(base64.b64decode(message["data"])),
        "attributes": message.get("attributes", None),
        "message_id": message.get("messageId", None),
        "ordering_key": message.get("orderingKey", None),
        "publish_time": message.get("publishTime", None),
    }

    if decoded["publish_time"] is not None:
        decoded["publish_time"] = isoparse(decoded["publish_time"])

    return decoded
