# Django GCP

`django-gcp` is a library of tools to help you deploy and use Django on Google Cloud Platform.
Helpers are provided for:

- [Cloud Storage](https://cloud.google.com/storage) (see [Storage](storage.md)),
- [Events from Pub/Sub and Eventarc](https://cloud.google.com/pubsub) (see [Events](events.md)),
- [Structured Cloud Logging](https://cloud.google.com/logging) and [Error Reporting](https://cloud.google.com/error-reporting) (see [Logs](logs.md)),
- [Cloud Run metadata](https://cloud.google.com/run/docs/container-contract#metadata-server) (see [Cloud Run](cloud-run.md)),
- [Cloud Tasks](https://cloud.google.com/tasks) and [Cloud Scheduler](https://cloud.google.com/scheduler) (see [Tasks](tasks/index.md)), and
- [Cloud Workflows](https://cloud.google.com/workflows) (see [Workflows](workflows/index.md)).

!!! note

    This library is used in production by several apps, but it is still early in development.
    Like the idea of it? Please [star us on GitHub](https://github.com/octue/django-gcp) and
    contribute via the [issues board](https://github.com/octue/django-gcp/issues).

## Aims

The ultimate goals are to:

- **Allow serverless Django** for actual fully-fledged apps, not toybox tutorials.
- **Enable event-based integration** between Django and various GCP services.
- **Simplify the use of GCP resources in Django**, including Storage, Logging, Error Reporting, Run, Pub/Sub, Tasks, Scheduler, and Workflows.

!!! tip

    Combining modules is where this gets powerful. For example, if you have *both* a store *and* a
    Pub/Sub subscription to events on that store, Django can react whenever files or their metadata change.

## Background

To run a reasonably comprehensive Django server on GCP, we were previously using four or five
libraries. Each covered a small piece of functionality, and keeping them working involved a
long cycle of engaging maintainers, forking, patching, opening pull requests, and waiting for
releases. Many maintainers of those libraries have given up or are snowed under, which we have
a lot of compassion for.

Some, like `django-storages`, admirably maintain a uniform API across many compute providers.
We do not change providers often enough to need that, and would rather have the flexibility to
do platform-specific things. We will be using GCP for the foreseeable future, so we accept a
platform-specific API in exchange for access to the latest GCP features and best practices.

## Thanks

This project is heavily based on a couple of really great libraries, particularly
[django-storages](https://django-storages.readthedocs.io/en/latest/) and
[django-cloud-tasks](https://github.com/flamingo-run/django-cloud-tasks).
Thank you so much to the many authors of these libraries.

The library boilerplate comes from the
[django-rabid-armadillo](https://github.com/thclark/django-rabid-armadillo) template.

![Unhappy armadillo](images/unhappy_armadillo.jpg){ width="150" }
