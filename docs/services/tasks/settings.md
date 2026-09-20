# Tasks settings

There are a number of settings required to enable on-demand and scheduled tasks. We recommend
you go through the following one by one — they are listed in order of importance. All settings
across the library are indexed in the [settings reference](../../settings/django-settings.md).

## `GCP_TASKS_DEFAULT_QUEUE_NAME`

Type: `string` (required)

The name of the task queue on GCP used for on-demand tasks. This will be created (if not
already present) when you enqueue your first task.

## `GCP_TASKS_DOMAIN`

Type: `string` (required)

The base URL of the server to which tasks will be pushed. In production, this needs to be set
to the URL of your worker service (see [Deploying workers](workers.md)).

!!! tip

    In local development, set up [localtunnel](https://github.com/localtunnel/localtunnel) and
    use its `-s` option to give yourself an amusing subdomain. You can then set
    `GCP_TASKS_DOMAIN = "https://king-julian-in-da-house.loca.lt"` in your local environment
    and receive `https://` traffic.

    That is awesome because, assuming you have installed local credentials per
    [Authenticating the server](../../authentication/server.md#locally), it allows you to spin up
    actual real queues and schedules on GCP to get a feel for how this all works.

## `GCP_TASKS_INVOKER_SERVICE_ACCOUNT_EMAILS`

Type: `list` of `string`

Default: absent (falls back to
[`GCP_INVOKER_SERVICE_ACCOUNT_EMAILS`](../../authentication/endpoints.md#gcp_invoker_service_account_emails))

The allow-list of service account emails permitted to invoke the tasks and subscriber-tasks
endpoints — typically the service account your queues, scheduler jobs, and push
subscriptions send with. When both this setting and the shared fallback are absent, every
caller is rejected. See [Authenticating endpoints](../../authentication/endpoints.md) for
how verification works.

## `GCP_TASKS_DISABLE_AUTH`

Type: `boolean`

Default: `False`

If set to `True`, the tasks and subscriber-tasks endpoints skip token verification entirely
and accept every request. Only do this where the endpoints are
[secured by other means](../../authentication/endpoints.md#disabling-authentication).

## `GCP_TASKS_RESOURCE_AFFIX`

Type: `string`

Default: `None`

A label affixed to the names of all resources created by `django-gcp`. It is highly
recommended that you set this, to avoid confusion about which resources belong to which
application and to enable cleanup of old resources.

If left unset, no affix is applied. That might be exactly what you want: for example, if you
manage all your task queues and scheduler jobs on existing infrastructure or with Terraform,
your own naming convention may already apply.

!!! warning

    Without `GCP_TASKS_RESOURCE_AFFIX`, `django-gcp` cannot clean up after itself, so you will
    have to remove old resources manually. Also make sure you do not have multiple independent
    Django apps with the same affix, or one app may delete resources belonging to another.

!!! note

    `SubscriberTask` subclasses do not automatically add the affix to the topic name they
    listen to. This allows you to subscribe to any topic on GCP for triggering tasks; if you
    want to use the affix, you can do so when overriding `topic_name`.

## `GCP_TASKS_REGION`

Type: `string`

Default: `"europe-west1"`

The region in which resources (task queues, scheduler jobs, and Pub/Sub topics) are accessed
and/or created.

## `GCP_TASKS_DELIMITER`

Type: `string`

Default: `"--"`

The delimiter used when creating resource names with an affix or other identifier.

## `GCP_TASKS_EAGER_EXECUTE`

Type: `boolean`

Default: `False`

If set to `True`, tasks execute synchronously when their `enqueue()` method is called (for
example, within a request). While not generally useful in production, this can be quite
helpful for straightforward debugging of tasks in local environments.

## `GCP_TASKS_DISABLE_EXECUTE`

Type: `boolean`

Default: `False`

If set to `True`, tasks are not enqueued for processing when their `enqueue()` or
`enqueue_later()` methods are called. Instead, the method simply returns `None` without
enqueuing the task. This can be useful when task execution needs to be temporarily disabled,
or when testing and debugging task code.

Note that this setting only affects the `enqueue()` and `enqueue_later()` methods; tasks can
still be executed manually even when it is `True`.

## `GCP_TASKS_EMULATOR_TARGET`

Type: `string` or `None`

Default: `None`

The address (for example `"127.0.0.1:8123"`) of a local Cloud Tasks emulator. When set, tasks
are sent to the emulator over an insecure gRPC transport instead of to the real Cloud Tasks
service. When unset, the GCP tasks client constructs its own transport and talks to the real
service.

## Environment variables

The tasks backend resolves its project, location, and service account from the process
environment, not from Django settings. For each, it uses an explicitly-provided value if
there is one, then the corresponding environment variable below, then a value derived from
the authenticated credentials:

- `GCP_PROJECT`: the project in which task queues, scheduler jobs, and subscriptions are
  managed.
- `GCP_LOCATION`: the location used for those resources (falling back to the project's
  default location; see also [`GCP_TASKS_REGION`](#gcp_tasks_region)).
- `GCP_SERVICE_ACCOUNT`: the service account used by the tasks backend.

These are indexed with the library's other environment variables in
[Environment variables](../../settings/environment-variables.md).
