# Events

This module provides a simple interface allowing Django to absorb events, for example from
Pub/Sub push subscriptions or Eventarc.

Events are communicated using Django's signals framework. They can be handled by any app (not
just `django-gcp`) simply by creating a signal receiver.

The events endpoints verify their callers and reject all requests until an allow-list is
configured — see [Authenticating endpoints](../authentication/endpoints.md) and
[Authenticating event pushes](#authenticating-event-pushes) below.

## Events endpoints

If you have `django_gcp` installed correctly (see
[Add the endpoints](../getting-started.md#add-the-endpoints)), running
`python manage.py show_urls` will show the endpoints for events.

Endpoints are `POST`-only and take two URL parameters, an `event_kind` and an
`event_reference`. The body of the `POST` request forms the `event_payload`.

So, if you `POST` data to `https://your-server.com/django-gcp/events/my-kind/my-reference/`,
a signal is dispatched with `event_kind="my-kind"` and `event_reference="my-reference"`.

## Authenticating event pushes

The events endpoint requires every request to carry a Google OIDC identity token from an
allowed caller; how verification works, how to configure senders, and how the settings
interact are described in [Authenticating endpoints](../authentication/endpoints.md). The
events-specific settings are the following.

### `GCP_EVENTS_INVOKER_SERVICE_ACCOUNT_EMAILS`

Type: `list` of `string`

Default: absent (falls back to
[`GCP_INVOKER_SERVICE_ACCOUNT_EMAILS`](../authentication/endpoints.md#gcp_invoker_service_account_emails))

The allow-list of service account emails permitted to invoke the events endpoint — typically
the service account of your Pub/Sub push subscriptions or Eventarc triggers. When both this
setting and the shared fallback are absent, every caller is rejected.

### `GCP_EVENTS_DISABLE_AUTH`

Type: `boolean`

Default: `False`

If set to `True`, the events endpoint skips token verification entirely and accepts every
request. Only do this where the endpoint is
[secured by other means](../authentication/endpoints.md#disabling-authentication).

## Creating a receiver

This is how you attach your handler. In your app's `signals.py` file, do:

```python
import logging
from django.dispatch import receiver
from django_gcp.events.signals import event_received
from django_gcp.events.utils import decode_pubsub_message


logger = logging.getLogger(__name__)


@receiver(event_received)
def receive_event(sender, event_kind, event_reference, event_payload, event_parameters):
    """Handle question updates received via pubsub
    :param event_kind (str): A kind/variety allowing you to determine the handler to use (eg "something-update"). Required.
    :param event_reference (str): A reference value provided by the client allowing events to be sorted/filtered. Required.
    :param event_payload (dict, array): The event payload to process, already decoded.
    :param event_parameters (dict): Extra parameters passed to the endpoint using URL query parameters
    :return: None
    """
    # There could be many different event kinds, from your own or other apps, and from
    # django-gcp itself, so make sure you only act on the specific kind(s) you want to handle.
    if event_kind == "something-important":
        # Here is where you handle the event using whatever logic you want. The caller has
        # already been authenticated, but you should still validate the payload's contents.
        print("DO SOMETHING IMPORTANT WITH THE PAYLOAD:", event_payload)

        # Your payload can be from any arbitrary source, and is in the form of decoded JSON.
        # However, if the source is Eventarc or Pub/Sub, the payload contains a formatted
        # message with base64-encoded data; we provide a utility to further decode this into
        # something sensible:
        message = decode_pubsub_message(event_payload)
        print("DECODED PUBSUB MESSAGE:", message)
```

!!! tip

    To handle a range of events, use a uniform prefix for all their kinds:

    ```python
    if event_kind.startswith("my-"):
        my_handler(event_kind, event_reference, event_payload)
    ```

## Generating endpoint URLs

A utility is provided to help generate URLs for the events endpoint. This is similar to, but
easier than, generating URLs with Django's built-in `reverse()` function.

It generates absolute URLs by default, because integration with external systems is the most
common use case.

```python
from django_gcp.events.utils import get_event_url

get_event_url(
    "the-kind",
    "the-reference",
    event_parameters={"a": "parameter"},  # Encoded as a querystring and decoded back to a dict by the events endpoint. Keep it short!
    url_namespace="gcp-events",  # You only need to edit this if you define your own urlpatterns with a different namespace
)
```

Including a secret token in `event_parameters` and checking it in your signal receiver was
once the recommended way to protect the endpoint. Now that
[callers are authenticated](#authenticating-event-pushes), such a token is no longer
necessary, though you may keep one as defence-in-depth.

!!! tip

    By default, `get_event_url` generates an absolute URL using the configured
    `settings.BASE_URL`. To specify a different base URL, pass it explicitly:

    ```python
    relative_url = get_event_url(
        "the-kind",
        "the-reference",
        base_url="",
    )

    non_default_base_url = get_event_url(
        "the-kind",
        "the-reference",
        base_url="https://somewhere.else.com",
    )
    ```

## Generating and consuming Pub/Sub messages

When hooked up to GCP Pub/Sub or Eventarc, the event payload is in the form of a Pub/Sub
message. These messages have a
[specific format](https://cloud.google.com/pubsub/docs/reference/rest/v1/PubsubMessage).

To allow you to interact directly with Pub/Sub (that is, publish messages to a topic), or to
test your signals, `django-gcp` includes a `make_pubsub_message` utility that provides an easy,
pythonic way of constructing a Pub/Sub message.

For example, to test the signal receiver above with a replica of a real Pub/Sub message payload:

```python
from datetime import datetime
from django_gcp.events.utils import make_pubsub_message


class YourTests(TestCase):
    def test_your_code_handles_a_payload_from_pubsub(self):
        payload = make_pubsub_message({"my": "data"}, publish_time=datetime.now())

        response = self.client.post(
            reverse("gcp-events", args=["the-event-kind", "the-event-reference"]),
            data=payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
```

## Exception handling

Any exception raised in a handler is hidden from the caller, to prevent disclosure of
information that could lead to an attack. Instead, a `400 BAD_REQUEST` status code is returned
with a generic error message.

!!! note

    We plan to add a way of returning more useful information to the caller, probably based on
    raising a `ValidationError` (much like using DRF serialisers). This is low priority right
    now, so if you need the feature, ping us on GitHub.
