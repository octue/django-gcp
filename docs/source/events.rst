.. _events:

Events
======

This module provides a simple interface allowing django to absorb events, eg from Pub/Sub push subscriptions or EventArc.

Events are communicated using django's signals framework. They can be handled by any app (not just django-gcp) simply by
creating a signal receiver.

.. WARNING::
    Please see :ref:`authenticating_webhooks_and_pubsub_messages` to learn about authenticating incoming messages

Events Endpoints
----------------

If you have ``django_gcp`` installed correctly (see :ref:`add_the_endpoints`), using ``python manage.py show_urls``
will show the endpoints for events.

Endpoints are ``POST``-only and require two URL parameters, an ``event_kind`` and an ``event_reference``. The body of the ``POST`` request forms the ``event_payload``.

So, if you ``POST`` data to ``https://your-server.com/django-gcp/events/my-kind/my-reference/`` then a signal will be dispatched
with ``event_kind="my-event"`` and ``event_reference="my-reference"``.

Creating A Receiver
-------------------

This is how you attach your handler. In ``your-app/signals.py`` file, do:

.. code-block:: python

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
       # There could be many different event types, from your own or other apps, and
       # django-gcp itself (when we get going with some more advanced features)
       # so make sure you only act on the specific kind(s) you want to handle
       if event_kind is "something-important":
           # Here is where you handle the event using whatever logic you want
           # CAREFUL: See the tip above about authentication (verifying the payload is not malicious)
           print("DO SOMETHING IMPORTANT WITH THE PAYLOAD:", event_payload)
           #
           # Your payload can be from any arbitrary source, and is in the form of decoded json.
           # However, if the source is Eventarc or Pub/Sub, the payload contains a formatted message
           # with base64 encoded data; we provide a utility to further decode this into something sensible:
           message = decode_pubsub_message(event_payload)
           print("DECODED PUBSUB MESSAGE:" message)

.. tip::

   To handle a range of events, use a uniform prefix for all their kinds, eg:

   .. code-block:: python

      if event_kind.startswith("my-"):
          my_handler(event_kind, event_reference, event_payload)


.. _generating_endpoint_urls:

Generating Endpoint URLs
------------------------

A utility is provided to help generate URLs for the events endpoint.
This is similar to, but easier than, generating URLs with django's built-in ``reverse()`` function.

It generates absolute URLs by default, because integration with external systems is the most common use case.

.. code-block:: python

   import logging
   from django_gcp.events.utils import get_event_url

   logger = logging.getLogger(__name__)

   get_event_url(
       'the-kind',
       'the-reference',
       event_parameters={"a":"parameter"},  # These get encoded as a querystring, and are decoded back to a dict by the events endpoint. Keep it short!
       url_namespace="gcp-events",  # You only need to edit this if you define your own urlpatterns with a different namespace
   )

.. tip::

   By default, ``get_event_url`` generates an absolute URL, using the configured ``settings.BASE_URL``.
   To specify a different base url, you can pass it explicitly:

   .. code-block:: python

      relative_url = get_event_url(
          'the-kind',
          'the-reference',
          base_url=''
      )

      non_default_base_url = get_event_url(
          'the-kind',
          'the-reference',
          base_url='https://somewhere.else.com'
      )


Generating and Consuming Pub/Sub Messages
-----------------------------------------

When hooked up to GCP Pub/Sub or eventarc, the event payload is in the form of a Pub/Sub message.

These messages have a specific format (see https://cloud.google.com/pubsub/docs/reference/rest/v1/PubsubMessage).

To allow you to interact directly with Pub/Sub (i.e. publish messages to a topic), or for the purposes of testing your signals,
``django-gcp`` includes a `make_pubsub_message` utility that provides an easy and pythonic way of constructing a Pub/Sub message.

For example, to test the signal receiver above with a replica of a real pubsub message payload, you might do:

.. code-block:: python

    from django_gcp.events.utils import make_pubsub_message
    from datetime import datetime

    class YourTests(TestCase):
        def test_your_code_handles_a_payload_from_pubsub(self):
            payload = make_pubsub_message({"my": "data"}, publish_time=datetime.now())

            response = self.client.post(
                reverse("gcp-events", args=["the-event-kind", "the-event-reference"]),
                data=payload,
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 201)


Exception Handling
------------------

Any exception that gets raised in the handlers will be hidden from the user
to prevent disclosure of information that may lead to attack.

Instead, a ``BAD_REQUEST (400)`` status code is returned with a generic error message.

.. note::
   We'll work on adding a way of returning more useful information to the end user,
   which will probably be based on raising a ValidationError or similar, a bit like
   using DRF serialisers.

   However, this is low priority right now so as always, if you need this feature,
   ping us on GitHub!
