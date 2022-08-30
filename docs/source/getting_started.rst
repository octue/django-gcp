.. _getting_started:

===============
Getting Started
===============

.. TIP::
    A **complete example of a working server** with django-gcp is provided in `the tests folder of the source code <https://github.com/octue/django-gcp/tree/main/tests/server>`_.

.. _install_the_library

Install the library
===================

**django-gcp** is available on `pypi <https://pypi.org/>`_, so installation into your python virtual environment is dead
simple:

.. code-block:: py

    poetry add django-gcp

Not using poetry? It's highly opinionated, but it's your friend. Google it.


.. _install_the_django_app:

Install the django app
======================

Next, you'll need to install this as an app in your django settings:

.. code-block:: py

    INSTALLED_APPS = [
        # ...
        'django_gcp'
        # ...
    ]


.. _add_the_endpoints:

Add the endpoints
=================

.. TIP::
    If you're only using storage, and not events or tasks, you can skip this step.

Include the django-gcp URLS in your ``your_app/urls.py``:

.. code-block:: python

   from django.urls import include, re_path
   from django_gcp import urls as django_gcp_urls

   urlpatterns = [
      # ...other routes
      # Use whatever regex you want:
      re_path(r"^django-gcp/", include(django_gcp_urls))
   ]

Using ``python manage.py show_urls`` you can now see the endpoints for both events and tasks appear in your app.
