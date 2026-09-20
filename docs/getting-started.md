# Getting started

!!! tip

    A **complete example of a working server** using `django-gcp` is provided in
    [the tests folder of the source code](https://github.com/octue/django-gcp/tree/main/tests/server).

## Install the library

`django-gcp` is available on [PyPI](https://pypi.org/project/django-gcp/), so you can install it
into your environment with your preferred package manager:

```bash
uv add django-gcp
# or
pip install django-gcp
```

## Install the Django app

Next, install `django-gcp` as an app in your Django settings:

```python
INSTALLED_APPS = [
    # ...
    "django_gcp",
    # ...
]
```

## Setting up the environment

Your server authenticates to GCP with Service Account Credentials or Application Default
Credentials — on Google infrastructure these are usually picked up automatically, and
elsewhere you point the `GOOGLE_APPLICATION_CREDENTIALS` environment variable at a
credentials file. See [Authenticating the server](authentication/server.md) for the full
options, including local development and GitHub Actions.

Two root-level Django settings span the library, both usually left unset:

### `GCP_PROJECT_ID`

Type: `string` or `None`

Default: `None`

The Google Cloud project ID. In most cases this can be left unset, because the project is
inferred from your credentials. Set it explicitly when the inference is wrong — for example,
when your service account has privileges across several projects and resources must be
accessed in a specific one. It can be overridden per storage store with the
[`project_id` option](services/storage.md#project_id).

### `GCP_CREDENTIALS`

Type: a `google.auth` credentials object, or `None`

Default: `None`

An explicit credentials object. In most deployments you should leave this unset and
authenticate via the environment instead (see
[Authenticating the server](authentication/server.md)). It can be overridden per storage
store with the [`credentials` option](services/storage.md#credentials).

Everything the library reads from your Django configuration and from the process environment
is indexed under [Django settings](settings/django-settings.md) and
[Environment variables](settings/environment-variables.md).

## Add the endpoints

!!! tip

    If you are only using storage, and not events or tasks, you can skip this step.

Include the `django-gcp` URLs in your `your_app/urls.py`:

```python
from django.urls import include, re_path
from django_gcp import urls as django_gcp_urls

urlpatterns = [
    # ...other routes
    # Use whatever regex you want:
    re_path(r"^django-gcp/", include(django_gcp_urls)),
]
```

Using `python manage.py show_urls` you can now see the endpoints for both events and tasks in
your app. These endpoints verify their callers and reject all requests until an allow-list is
configured — see [Authenticating endpoints](authentication/endpoints.md).

## Using terraform

We recommend managing your GCP infrastructure — service accounts, IAM bindings, buckets, task
queues, subscriptions, scheduler jobs, and workflows — with terraform or another dedicated
infrastructure-as-code tool, rather than creating resources by hand in the console. Declared
infrastructure is reviewable, reproducible, and much easier to keep consistent with the
settings this library reads.

The [root of this repository](https://github.com/octue/django-gcp) contains a terraform
module defining the infrastructure used for live integration testing, which you can use as a
reference for the resources a `django-gcp` deployment needs. Octue also maintains
[terraform modules for django applications on GCP](https://github.com/orgs/octue/repositories?q=terraform-octue-django),
which are a useful starting point for a production deployment.
