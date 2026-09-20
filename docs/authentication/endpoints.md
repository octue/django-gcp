# Authenticating endpoints

Every endpoint that `django-gcp` exposes — for [events](../services/events.md),
[tasks](../services/tasks/index.md), and subscriber tasks — verifies a Google OIDC identity
token on every request. Until you configure an allow-list of caller identities, every request
is rejected: the endpoints are secure by default.

!!! note

    Built-in endpoint authentication was introduced in version 0.27.0 as a breaking change.
    Migration instructions are in the release notes on the
    [GitHub releases page](https://github.com/octue/django-gcp/releases).

## How verification works

A request must carry an identity token in an `Authorization: Bearer <token>` header. The
token's signature is verified against Google's public certificates, and its audience must
equal the request's absolute URI — either without its query string (the audience used by
tokens that `django-gcp` senders attach, and by typical workflow calls) or with it (the
default audience Pub/Sub attaches to push requests). The token's claims must have
`email_verified` set and an `email` present in the configured allow-list.

A request with a missing or invalid token receives `401 Unauthorized`; a valid token whose
email is not in the allow-list receives `403 Forbidden`. On success, the verified claims are
attached to the request as `request.oidc_claims`, so your task or signal-receiver code can
inspect the caller's identity.

All authentication settings are read per-request, so they can be changed (for example with
`override_settings` in tests) without restarting the server.

## Configuring the allow-list

The allow-list is a list of service account emails permitted to invoke your endpoints. In
the common case of one invoker identity across all services, set the shared setting:

```python
GCP_INVOKER_SERVICE_ACCOUNT_EMAILS = ["invoker@my-project.iam.gserviceaccount.com"]
```

Each endpoint resolves its allow-list from the first of an ordered tuple of settings that is
present, so a service-specific setting overrides the shared one:

- The tasks and subscriber-tasks endpoints consult
  [`GCP_TASKS_INVOKER_SERVICE_ACCOUNT_EMAILS`](../services/tasks/settings.md#gcp_tasks_invoker_service_account_emails),
  then [`GCP_INVOKER_SERVICE_ACCOUNT_EMAILS`](#gcp_invoker_service_account_emails).
- The events endpoint consults
  [`GCP_EVENTS_INVOKER_SERVICE_ACCOUNT_EMAILS`](../services/events.md#gcp_events_invoker_service_account_emails),
  then [`GCP_INVOKER_SERVICE_ACCOUNT_EMAILS`](#gcp_invoker_service_account_emails).
- [Endpoints you add yourself](adding-authenticated-endpoints.md) consult whichever
  settings you configure them with, defaulting to
  [`GCP_INVOKER_SERVICE_ACCOUNT_EMAILS`](#gcp_invoker_service_account_emails) — for
  example, [workflow-called endpoints](../services/workflows/usage.md#verifying-calls-made-by-workflows)
  consult `GCP_WORKFLOWS_INVOKER_SERVICE_ACCOUNT_EMAILS`, then the shared setting.

If none of the consulted settings is present, the allow-list is empty and every caller is
rejected.

### `GCP_INVOKER_SERVICE_ACCOUNT_EMAILS`

Type: `list` of `string`

Default: absent

The shared fallback allow-list for all OIDC-gated endpoints. Each entry is the email of a
service account permitted to invoke the endpoints. When this setting is absent and no
service-specific setting is present either, every caller is rejected.

## Enabling OIDC authentication of senders

Every sender must attach an OIDC identity token, for a service account in your allow-list,
to the requests it makes. A subscription, queue, or job configured without OIDC
authentication — for example one created through the console, `gcloud`, Terraform, or other
application code — sends no token (or a token for the wrong service account or audience),
so its requests are rejected.

!!! note

    Senders created using `django-gcp` — Cloud Tasks tasks, Cloud Scheduler jobs for
    periodic tasks, and Pub/Sub push subscriptions for `SubscriberTask` subclasses —
    already have OIDC authentication enabled, with an audience matching the endpoint URL.
    Those deployments only need the allow-list settings above.

For a Pub/Sub push subscription, with `gcloud`:

```bash
gcloud pubsub subscriptions update SUBSCRIPTION_NAME \
    --push-endpoint=https://your-server.com/django-gcp/events/the-kind/the-reference \
    --push-auth-service-account=invoker@my-project.iam.gserviceaccount.com
```

or in Terraform, inside the `push_config` block of a `google_pubsub_subscription`:

```hcl
push_config {
  push_endpoint = "https://your-server.com/django-gcp/events/the-kind/the-reference"
  oidc_token {
    service_account_email = "invoker@my-project.iam.gserviceaccount.com"
  }
}
```

For a Cloud Scheduler job, with `gcloud`:

```bash
gcloud scheduler jobs update http JOB_NAME \
    --oidc-service-account-email=invoker@my-project.iam.gserviceaccount.com \
    --oidc-token-audience=https://your-server.com/django-gcp/tasks/YourPeriodicTask
```

or in Terraform, inside the `http_target` block of a `google_cloud_scheduler_job`:

```hcl
http_target {
  uri = "https://your-server.com/django-gcp/tasks/YourPeriodicTask"
  oidc_token {
    service_account_email = "invoker@my-project.iam.gserviceaccount.com"
    audience              = "https://your-server.com/django-gcp/tasks/YourPeriodicTask"
  }
}
```

For Cloud Tasks tasks created by code other than `django-gcp`, set the `oidc_token` field on
each task's `http_request` — see
[Creating HTTP target tasks](https://cloud.google.com/tasks/docs/creating-http-target-tasks).

## Behind a reverse proxy

The audience check compares the token's audience against the request's absolute URI as
reconstructed by Django. Behind a TLS-terminating proxy or load balancer, Django must be
configured to reconstruct the externally visible URL: set
[`SECURE_PROXY_SSL_HEADER`](https://docs.djangoproject.com/en/stable/ref/settings/#secure-proxy-ssl-header)
(and [`USE_X_FORWARDED_HOST`](https://docs.djangoproject.com/en/stable/ref/settings/#use-x-forwarded-host)
where the proxy rewrites the host header), and ensure
[`GCP_TASKS_DOMAIN`](../services/tasks/settings.md#gcp_tasks_domain) matches the externally
visible scheme and host. Otherwise the reconstructed URI has the wrong scheme or host, and
valid tokens are rejected with `401 Unauthorized`.

## Disabling authentication

Verification can be switched off per service with
[`GCP_TASKS_DISABLE_AUTH`](../services/tasks/settings.md#gcp_tasks_disable_auth) (covering
both the tasks and subscriber-tasks endpoints) and
[`GCP_EVENTS_DISABLE_AUTH`](../services/events.md#gcp_events_disable_auth) (covering the
events endpoint).

For per-URL control, wire the views yourself instead of including `django_gcp.urls`, passing
`auth_required=False` (or a fixed `allowed_service_account_emails` list) to `as_view()`. The
URL names `gcp-events`, `gcp-subscriber-tasks`, and `gcp-tasks` must be preserved, because
`Task.url()` and `get_event_url()` reverse them:

```python
from django.urls import path
from django_gcp.events.views import GoogleCloudEventsView
from django_gcp.tasks.views import GoogleCloudSubscriberTaskView, GoogleCloudTaskView

urlpatterns = [
    path(r"events/<event_kind>/<event_reference>", GoogleCloudEventsView.as_view(auth_required=False), name="gcp-events"),
    path(r"subscriber-tasks/<task_name>", GoogleCloudSubscriberTaskView.as_view(), name="gcp-subscriber-tasks"),
    path(r"tasks/<task_name>", GoogleCloudTaskView.as_view(allowed_service_account_emails=["invoker@my-project.iam.gserviceaccount.com"]), name="gcp-tasks"),
]
```

!!! warning

    Only disable authentication where the endpoints are secured by other means —
    infrastructure ingress restriction combined with IAM invoker permissions, so that
    unauthenticated requests never reach Django. Do not disable it merely because an
    externally created subscription, queue, or job does not yet send a token: update the
    sender instead (see [above](#enabling-oidc-authentication-of-senders)), because a
    disabled endpoint is open to anyone who can reach it.
