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
your app. Before exposing these endpoints publicly, read
[Authenticating events and tasks](authentication/events-and-tasks.md); they do not authenticate
their callers out of the box.
