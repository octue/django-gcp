.. _authenticating_webhooks_and_pubsub_messages:

Authenticating Webhooks and PubSub messages
===========================================

.. warning::

   We are yet to add the ability to accept `_JWT-authenticated push subscriptions <https://cloud.google.com/pubsub/docs/push?&_ga=2.57385448.-318721115.1638533188#validate_tokens>`_ from PubSub, EventArc, Cloud Tasks
   or Cloud Scheduler so that authentication is handled out of the box.

   In the meantime, it's your responsibility to ensure that your handlers are protected (or otherwise wrap the
   urls in a decorator to manage authentication).

   The best way of doing this is to generate a single use token and supply it as an event parameter (see :ref:`generating_endpoint_urls`_).

   We want to work on this so if you'd like to sponsor that, find us on GitHub!
