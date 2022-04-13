.. _events:

Events
======

This module provides a simple interface allowing django to absorb events, eg from Pub/Sub push subscriptions or EventArc.

Events are communicated using django's signals framework. They can be handled by any app (not just django-gcp) simply by
creating a signal receiver.

About Authentication
--------------------

.. warning::

   We are yet to add the ability to accept JWT-authenticated push subscriptions from PubSub/EventArc
   so that authentication is handled out of the box.

   In the meantime, it's your responsibility to ensure that your handlers are protected (or otherwise wrap the
   urls in a decorator to manage authentication).

   The best way of doing this is to generate a single use token and supply it as an event parameter (see `Generating Endpoint URLs`_).

   As always, if you want us to help, find us on GitHub!


Adding Endpoints
----------------

In ``your_app/urls.py`` you'll want to include the django-gcp URLs:

.. code-block:: python

   from django.urls import include, re_path
   from django_gcp import urls as django_gcp_urls


   urlpatterns = [
      # ...other routes
      # Use whatever regex you want:
      re_path(r"^django-gcp/", include(django_gcp_urls))
   ]

Using ``python manage.py show_urls`` you can see the endpoint appear in your app.

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


   logger = logging.getLogger(__name__)


   @receiver(event_received)
   def receive_event(sender, event_kind, event_reference, event_payload):
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
           print("DO SOMETHING IMPORTANT")

.. tip::

   To handle a range of events, use a uniform prefix for all their kinds, eg:

   .. code-block:: python

      if event_kind.startswith("my-"):
          my_handler(event_kind, event_reference, event_payload)

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
