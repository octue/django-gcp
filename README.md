[![PyPI version](https://badge.fury.io/py/django_gcp.svg)](https://badge.fury.io/py/django_gcp)
[![codecov](https://codecov.io/gh/octue/django-gcp/branch/main/graph/badge.svg?token=H2QLSCF3DU)](https://codecov.io/gh/octue/django-gcp)
[![Documentation](https://readthedocs.org/projects/django-gcp/badge/?version=latest)](https://django-gcp.readthedocs.io/en/latest/?badge=latest)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

# DjangoGCP

Helps you to run Django on Google Cloud Platform:

- Storage (including direct uploads)
- Events (PubSub)
- Tasks (ad-hoc and scheduled)
- Logging (pretty colours and labels) and
- Error Reporting.

Read the [documentation here](https://django-gcp.readthedocs.io/en/latest).

This app is maintained by Octue - we're on a mission to help climate scientists and energy engineers be more efficient. [Find out more](https://www.octue.com). If you need some help implementing `django-gcp`, or wish to sponsor a feature or any of the issues on the board, we can help! Raise an issue or [contact us](https://www.octue.com/contact).

## Are you from GCP??

If so, get in touch for a chat. We're doing fun things with Google Cloud. Way funner than boring old django... :)

## All the :heart:

This app is based heavily on [django-storages](https://django-storages.readthedocs.io/en/latest/), [django-google-cloud-tasks](https://github.com/flamingo-run/django-cloud-tasks) and uses the [django-rabid-armadillo](https://github.com/thclark/django-rabid-armadillo) template. Big love.

## Contributing

It's pretty straightforward to get going, but it's good to get in touch first, especially if you're planning a big feature.

### Set up

Open the project in codespaces, a vscode .devcontainer (which is configured out of the box for you) or your favourite IDE or editor (if the latter you'll need to set up `docker compose` yourself).

Create a file `.devcontainer/docker-compose.developer.yml`. This allows you to customise extra services and volumes you make available to the container.
For example, you can map your own gcloud config folder into the container to use your own credentials. This example will get you going, but you can just leave the services key empty.

```
version: "3.8"

services:
  web:
    volumes:
      - ..:/workspace:cached
      - $HOME/.config/gcloud:/gcp/config

    environment:
      - CLOUDSDK_CONFIG=/gcp/config
      - GOOGLE_APPLICATION_CREDENTIALS=/gcp/config/your-credentials-file.json
```

### Initialise gcloud CLI

To sign in (enabling use of the gcloud CLI tool), do:

```
gcloud config set project octue-django-gcp
gcloud auth login
```

### Run the tests

Run the tests:

```
pytest .
```

We use pre-commit to ensure code quality standards (and to help us automate releases using conventional-commits). If you can get on board with this that's really helpful - if not, don't fret, we can help.

### Use the example app

You can start the example app (which is useful for seeing how `django-gcp` looks in the admin.

Initially, do:

```
python manage.py migrate
python manage.py createsuperuser
# make yourself a user account at the prompt
```

Then to run the app, do:

```
python manage.py runserver
```

...and visit [http://localhost:8000/admin/](http://localhost:8000/admin/) to sign in.

### Update the docs

We're pretty good on keeping the docs helpful, friendly and up to date. Any contributions should be
fully documented.

To help develop the docs quickly, we set up a watcher that rebuilds the docs on save. Start it with:

```
python docs/watch.py
```

Once docs are building, the the vscode live server extension (or whatever the equivalent is in your IDE)
to live-reload `docs/html/index.html` in your browser, then get started!
