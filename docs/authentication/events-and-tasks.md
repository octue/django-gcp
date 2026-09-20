# Authenticating events and tasks

The endpoints that `django-gcp` exposes for [events](../events.md) and [tasks](../tasks/index.md)
**do not authenticate their callers out of the box**. Anybody who can reach an events endpoint
can dispatch a signal into your application, and anybody who can reach a task endpoint can
trigger task execution.

!!! danger

    It is your responsibility to ensure that these endpoints are protected. Deploying them
    unprotected on a public URL means untrusted parties can inject events and invoke tasks.
    This limitation is tracked in
    [issue #7](https://github.com/octue/django-gcp/issues/7), which proposes verifying
    [JWT-authenticated push subscriptions](https://cloud.google.com/pubsub/docs/push#validate_tokens)
    from Pub/Sub, Eventarc, Cloud Tasks, and Cloud Scheduler so that authentication is handled
    out of the box. If you would like to sponsor that work, find us on GitHub.

Until built-in verification lands, protect the endpoints using one or more of the following:

1. **Restrict ingress at the infrastructure level.** Where possible, do not expose the worker
   service publicly at all: use Cloud Run ingress controls and IAM invoker permissions so only
   your Pub/Sub subscriptions, task queues, and scheduler jobs can reach it. This is the
   strongest protection, because the request never reaches Django unauthenticated.

2. **Supply a single-use or secret token as an event parameter.** Generate endpoint URLs with
   [`get_event_url`](../events.md#generating-endpoint-urls), including a token in
   `event_parameters`, and verify that token in your signal receiver before acting on the
   payload.

3. **Wrap the URLs in an authenticating decorator.** Rather than including `django_gcp.urls`
   directly, wrap the views with your own decorator that verifies an OIDC token or other
   credential attached to the push request.

## Workflow-called endpoints

Endpoints called back by Cloud Workflows _can_ be verified in-app today: `django-gcp` provides
the `workflow_oidc_required` decorator, which verifies the OIDC identity token that Cloud
Workflows attaches to its calls. See
[Verifying calls made by workflows](../workflows/usage.md#verifying-calls-made-by-workflows).
