[![PyPI version](https://badge.fury.io/py/django_gcp.svg)](https://badge.fury.io/py/django_gcp)
[![codecov](https://codecov.io/gh/octue/django_gcp/branch/master/graph/badge.svg)](https://codecov.io/gh/octue/django_gcp)
[![Documentation](https://readthedocs.org/projects/django_gcp/badge/?version=latest)](https://django_gcp.readthedocs.io/en/latest/?badge=latest)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

# DjangoGCP

Helps you to run Django on Google Cloud Platform - Storage, PubSub and Tasks.

Read the [documentation here](https://django_gcp.readthedocs.io/en/latest).

This app is maintained by Octue - we're on a mission to help climate scientists and energy engineers be more efficient. [Find out more](https://www.octue.com).

If you need some help implementing or updating this, we can help! Raise an issue or [contact us](https://www.octue.com/contact).

## Are you from GCP??

If so, get in touch for a chat. We're doing fun things with Google Cloud. Way funner than boring old django... :)

## All the :heart:

This app is based heavily on [django-storages](), [django-cloud-tasks]() and uses on the [django-rabid-armadillo]() template. Big love.

- Template django app, with:

## Contributing

It's pretty straightforward to get going, but it's good to get in touch first, especially if you're planning a big feature.

Open the project in codespaces, a vscode .devcontainer or your favourite IDE or editor (if the latter you'll need to set up docker-compose yourself), then:

```
poetry install
```

Run the tests:

```
pytest .
```

We use pre-commit to ensure code quality standards (and to help us automate releases using conventional-commits). If you can get on board with this that's really helpful - if not, don't fret, we can help.
