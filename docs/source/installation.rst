.. _installation:

============
Installation
============

**django-gcp** is available on `pypi <https://pypi.org/>`_, so installation into your python virtual environment is dead
simple:

.. code-block:: py

    poetry add django-gcp

Not using poetry? It's highly opinionated, but it's your friend. Google it.

Next, you'll need to install this as an app in your django settings:

.. code-block:: py

    INSTALLED_APPS = [
        ...
        'django_gcp'
        ...

Then run migrations:

.. code-block:: bash

    python manage.py makemigrations
