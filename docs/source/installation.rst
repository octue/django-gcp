.. _installation:

============
Installation
============

**django-rabid-armadillo** is available on `pypi <https://pypi.org/>`_, so installation into your python virtual environment is dead
simple:

.. code-block:: py

    poetry add django-rabid-armadillo

Not using poetry? It's highly opinionated, but it's your friend. Google it.

Next, you'll need to install this as an app in your django settings:

.. code-block:: py

    INSTALLED_APPS = [
        ...
        'rabid_armadillo'
        ...

Then run migrations:

.. code-block:: bash

    python manage.py makemigrations


.. _compilation:

Compilation
============

There is presently no need to compile **django-rabid-armadillo**, as it's written entirely in python. Yay.
