# Authentication

There are two aspects to authentication with `django-gcp`:

1. [Authenticating the server](server.md) so it can interact with GCP services, using Service
   Account Credentials or Application Default Credentials.
2. [Authenticating incoming events and tasks](events-and-tasks.md) — verifying that webhooks and
   Pub/Sub messages arriving at your endpoints genuinely come from the services you expect, and
   not from an attacker.

Both are required for a secure deployment. The first is about your server proving its identity to
Google; the second is about callers proving their identity to your server.
