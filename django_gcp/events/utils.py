import base64
from datetime import timezone
import json
import logging

from dateutil.parser import isoparse
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlencode

from django_gcp.exceptions import InvalidPubSubMessageError

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

    logger.debug("Generated webhook endpoint url %s", url)

    return url


def make_pubsub_message(
    data, subscription, attributes=None, message_id=None, ordering_key=None, publish_time=None, as_dict=False
):
    """Make a bytes object containing a message replicating the GCP Pub/Sub v1 format

    For more details see: https://cloud.google.com/pubsub/docs/reference/rest/v1/PubsubMessage

    Duplicated snake case keys found in "real" pubsub messages are not added, since they appear to be deprecated:
    https://stackoverflow.com/questions/73477187/why-do-gcp-pub-sub-messages-have-duplicated-message-id-and-publish-time-values

    :param Union[dict, list] data: JSON-serialisable data to form the body of the message
    :param str subscription: a subscription path which indicates the subscription that caused this message to be delivered, eg 'projects/my-project/subscriptions/my-subscription-name'
    :param Union[dict, None] attributes: Dict of attributes to attach to the message. Contents must be flat, containing only string keys with string values.
    :param Union[str, None] message_id: An optional id for the message.
    :param Union[str, None] ordering_key: A string used to order messages.
    :param Union[datetime, None] publish_time: If sending a message to PubSub, this will be set by the server on receipt so generally should be left as `None`. However, for the purposes of mocking messages for testing, supply a python datetime specifying the publish time of the message, which will be converted to a string timestamp with nanosecond accuracy.
    :param bool as_dict: If true, return the message as a dict instead of a utf-8-encoded json string
    :return bytes: A bytes object containing a fully composed PubSub message
    """
    message = dict()

    message["data"] = base64.b64encode(json.dumps(data).encode()).decode()

    if publish_time is not None:
        publish_time_utc_naive = _make_naive_utc(publish_time)
        iso_us = publish_time_utc_naive.isoformat()
        iso_ns = f"{iso_us}000Z"
        message["publishTime"] = iso_ns

    if attributes is not None:
        # Check all attributes are k-v pairs of strings
        for k, v in attributes.items():
            if k.__class__ != str:
                raise ValueError("All attribute keys must be strings")
            if v.__class__ != str:
                raise ValueError("All attribute values must be strings")
        message["attributes"] = attributes

    if message_id is not None:
        if message_id.__class__ != str:
            raise ValueError("The message_id, if given, must be a string")
        message["messageId"] = message_id

    if ordering_key is not None:
        if ordering_key.__class__ != str:
            raise ValueError("The ordering_key, if given, must be a string")
        message["orderingKey"] = ordering_key

    if subscription.__class__ != str:
        raise ValueError(
            "The subscription must be a string, like 'projects/my-project/subscriptions/my-subscription-name'"
        )

    if as_dict:
        return {"message": message, "subscription": subscription}

    return json.dumps({"message": message, "subscription": subscription}).encode("utf-8")


def decode_pubsub_message(body):
    """Decode data from a pubsub message body

    If the message data is json-decodable, then the decoded object's data field will contain the decoded object or array.
    Otherwise, the data field will contain a decoded string (pubsub messages comprising just a string are valid).

    :parameter Union[bytes, dict] body: The Pub/Sub message as a bytes object or as a decoded object
    :return: dict A flattened data structure containing message data and other information
    """
    if isinstance(body, bytes):
        body = json.loads(body)

    try:
        message = body["message"]
        subscription = body["subscription"]
        data = base64.b64decode(message["data"])

        # If data is json-decodable then do it. If it's just a string (which can be a valid message) accept that and decode it from bytes
        #   TODO determine if this try/catch is required. It was put there to handle raw strings coming in from pubsub, but unit tests show
        #   that the decoder will handle a single string
        try:
            data = json.loads(data)
        except json.decoder.JSONDecodeError:
            data = data.decode("utf-8")

        decoded = {
            "data": data,
            "attributes": message.get("attributes", None),
            "message_id": message.get("messageId", None),
            "ordering_key": message.get("orderingKey", None),
            "publish_time": message.get("publishTime", None),
            "subscription": subscription,
        }

    except KeyError as e:
        raise InvalidPubSubMessageError(
            f"Failed to decode Pub/Sub message (check the message conforms to Pub/Sub requirements: {body}"
        ) from e

    if decoded["publish_time"] is not None:
        decoded["publish_time"] = isoparse(decoded["publish_time"])

    return decoded
