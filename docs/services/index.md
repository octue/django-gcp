# Services

`django-gcp` is organised into modules, each integrating Django with one Google Cloud
service (or a small family of them). They are independent: use only the ones you need.

- **[Storage](storage.md)** — Google Cloud Storage backends for Django's `FileField` and
  static files, plus a `BlobField` supporting direct uploads and richer blob handling.
- **[Events](events.md)** — absorb events from Pub/Sub push subscriptions or Eventarc,
  dispatched through Django's signals framework.
- **[Tasks](tasks/index.md)** — push-based background tasks on Cloud Tasks, periodic tasks
  on Cloud Scheduler, and Pub/Sub-subscribed tasks, all runnable by serverless workers.
- **[Workflows](workflows/index.md)** — invoke and track Google Cloud Workflows
  orchestrations from Django.
- **[Logs](logs.md)** — structured Cloud Logging and Error Reporting handlers.
- **[Cloud Run](cloud-run.md)** — a wrapper for the Cloud Run metadata server.

Before using the events or tasks endpoints, read
[Authenticating events and tasks](../authentication/events-and-tasks.md); they do not
authenticate their callers out of the box.
