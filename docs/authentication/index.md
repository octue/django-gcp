# Authentication

There are two aspects to authentication with `django-gcp`:

1. [Authenticating the server](server.md) so it can interact with GCP services, using Service
   Account Credentials or Application Default Credentials.
2. [Authenticating endpoints](endpoints.md) — incoming events, tasks, and workflow callbacks
   are verified in-app by default: each request must carry a Google OIDC identity token from a
   caller on your configured allow-list.

Both are required for a secure deployment. The first is about your server proving its identity to
Google; the second is about callers proving their identity to your server.
