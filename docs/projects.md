# Projects

In most cases, the ID of the GCP project you are working on will be inferred from your
Application Default Credentials or Service Account (see
[Authentication](authentication/index.md)).

If that is not correct (for example, your service account has privileges across projects),
you may need to set it explicitly. How you do so differs by module, because the storage
module reads Django settings while the tasks backend reads environment variables. All
settings are indexed in the [settings reference](settings.md).

## Settings

### `GCP_PROJECT_ID`

Type: `string` or `None`

Default: `None`

The Google Cloud project ID used by the **storage** module's clients. If unset, the project
is inferred from the credentials. It can also be overridden per store by passing
`project_id` in the `OPTIONS` dict of an alias in the `STORAGES` setting (see
[Storage settings options](storage.md#storage-settings-options)).

### `GCP_CREDENTIALS`

Type: a `google.auth` credentials object, or `None`

Default: `None`

An explicit credentials object used by the **storage** module's clients. In most deployments
you should leave this unset and authenticate via the environment instead (see
[Authenticating the server](authentication/server.md)). Like `GCP_PROJECT_ID`, it can be
overridden per store by passing `credentials` in that store's `OPTIONS`.

## Environment variables

The **tasks** backend resolves its project, location, and service account differently: for
each, it uses an explicitly-provided value if there is one, then the corresponding
environment variable below, then a value derived from the authenticated credentials.

- `GCP_PROJECT`: the project in which task queues, scheduler jobs, and subscriptions are
  managed.
- `GCP_LOCATION`: the location used for those resources (falling back to the project's
  default location; see also [`GCP_TASKS_REGION`](tasks/settings.md#gcp_tasks_region)).
- `GCP_SERVICE_ACCOUNT`: the service account used by the tasks backend.
