# Adding authenticated endpoints

The verification used by the built-in endpoints is available for your own views, so you can
receive hooks from anywhere in the Google infrastructure that can attach an OIDC identity
token — Cloud Workflows callbacks, Cloud Scheduler jobs, Pub/Sub push subscriptions,
Eventarc triggers, or Cloud Tasks targets of your own. The
[same verification](endpoints.md#how-verification-works) applies: a bearer token with a
valid signature, an audience matching the request URI, and a verified email in an
allow-list. The sender must have
[OIDC authentication enabled](endpoints.md#enabling-oidc-authentication-of-senders).

Protect a function view with the `oidc_required` decorator:

```python
from django.http import JsonResponse
from django_gcp.auth import oidc_required


@oidc_required
def my_hook(request):
    # request.oidc_claims carries the verified token claims
    return JsonResponse({"caller": request.oidc_claims["email"]})
```

Used bare, the decorator reads its allow-list from
[`GCP_INVOKER_SERVICE_ACCOUNT_EMAILS`](endpoints.md#gcp_invoker_service_account_emails).
Two arguments alter that:

- `settings_names` — an ordered tuple of Django setting names to consult, so a group of
  endpoints can keep a dedicated allow-list with the shared setting as fallback:

  ```python
  @oidc_required(settings_names=("MY_HOOK_INVOKER_SERVICE_ACCOUNT_EMAILS", "GCP_INVOKER_SERVICE_ACCOUNT_EMAILS"))
  ```

- `allowed_service_account_emails` — a fixed list of caller emails for this endpoint alone,
  bypassing settings entirely.

Where a decorator does not fit, call `verify_oidc_token(request)` directly; it returns a
`(claims, error_response)` pair, and you return the error response (a 401 or 403) when it is
not `None`. Class-based views can mix in `OIDCAuthRequiredMixin`, which is how the built-in
endpoints are protected and accepts the same overrides as `as_view()` keyword arguments.

For a worked example use case — verifying the calls a Cloud Workflow makes back into Django
between steps — see
[Verifying calls made by workflows](../services/workflows/usage.md#verifying-calls-made-by-workflows).
