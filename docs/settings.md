# Settings reference

This page indexes every Django setting read by `django-gcp`, grouped by module. Each row
links to the full description in the relevant part of the documentation; the table itself
holds only the type and default.

!!! note

    Contributors: any setting added or updated must be fully described in the relevant module
    page **and** cross-referenced as a row here. See the
    [documentation conventions](conventions/documentation.md).

## Storage

Most storage configuration is per-store, passed via the `OPTIONS` dict for each alias in
Django's `STORAGES` setting; those options are described in
[Storage settings options](storage.md#storage-settings-options). The following root-level
settings also apply.

| Setting                                              | Type               | Default   | Details                                                    |
| ---------------------------------------------------- | ------------------ | --------- | ---------------------------------------------------------- |
| `GCP_PROJECT_ID`                                     | `string` or `None` | `None`    | [Projects](projects.md#gcp_project_id)                     |
| `GCP_CREDENTIALS`                                    | credentials object | `None`    | [Projects](projects.md#gcp_credentials)                    |
| `GCP_STORAGE_OVERRIDE_BLOBFIELD_VALUE`               | `boolean`          | `False`   | [Storage](storage.md#gcp_storage_override_blobfield_value) |
| `GCP_STORAGE_BLOBFIELD_MAX_SIZE_BYTES`               | `integer`          | unlimited | [Storage](storage.md#gcp_storage_blobfield_max_size_bytes) |
| `GCP_STORAGE_OVERRIDE_GET_DESTINATION_PATH_CALLBACK` | callable or `None` | `None`    | [Storage](storage.md#test-only-callback-overrides)         |
| `GCP_STORAGE_OVERRIDE_UPDATE_ATTRIBUTES_CALLBACK`    | callable or `None` | `None`    | [Storage](storage.md#test-only-callback-overrides)         |

## Events

| Setting    | Type     | Default                    | Details                                      |
| ---------- | -------- | -------------------------- | -------------------------------------------- |
| `BASE_URL` | `string` | required for absolute URLs | [Events](events.md#generating-endpoint-urls) |

## Tasks

| Setting                        | Type               | Default          | Details                                                          |
| ------------------------------ | ------------------ | ---------------- | ---------------------------------------------------------------- |
| `GCP_TASKS_DEFAULT_QUEUE_NAME` | `string`           | required         | [Tasks settings](tasks/settings.md#gcp_tasks_default_queue_name) |
| `GCP_TASKS_DOMAIN`             | `string`           | required         | [Tasks settings](tasks/settings.md#gcp_tasks_domain)             |
| `GCP_TASKS_RESOURCE_AFFIX`     | `string`           | `None`           | [Tasks settings](tasks/settings.md#gcp_tasks_resource_affix)     |
| `GCP_TASKS_REGION`             | `string`           | `"europe-west1"` | [Tasks settings](tasks/settings.md#gcp_tasks_region)             |
| `GCP_TASKS_DELIMITER`          | `string`           | `"--"`           | [Tasks settings](tasks/settings.md#gcp_tasks_delimiter)          |
| `GCP_TASKS_EAGER_EXECUTE`      | `boolean`          | `False`          | [Tasks settings](tasks/settings.md#gcp_tasks_eager_execute)      |
| `GCP_TASKS_DISABLE_EXECUTE`    | `boolean`          | `False`          | [Tasks settings](tasks/settings.md#gcp_tasks_disable_execute)    |
| `GCP_TASKS_EMULATOR_TARGET`    | `string` or `None` | `None`           | [Tasks settings](tasks/settings.md#gcp_tasks_emulator_target)    |

## Workflows

| Setting                                        | Type   | Default                       | Details                                                                 |
| ---------------------------------------------- | ------ | ----------------------------- | ----------------------------------------------------------------------- |
| `GCP_WORKFLOWS_INVOKER_SERVICE_ACCOUNT_EMAILS` | `list` | absent (all callers rejected) | [Workflows usage](workflows/usage.md#verifying-calls-made-by-workflows) |

## Logs

| Setting                            | Type     | Default                      | Details                         |
| ---------------------------------- | -------- | ---------------------------- | ------------------------------- |
| `GCP_ERROR_REPORTING_SERVICE_NAME` | `string` | required for Error Reporting | [Logs](logs.md#error-reporting) |

## Environment variables

These are read from the process environment, not from Django settings.

| Variable                         | Details                                                                                        |
| -------------------------------- | ---------------------------------------------------------------------------------------------- |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to a credentials file — see [Authenticating the server](authentication/server.md#locally) |
| `GCP_PROJECT`                    | Tasks backend project fallback — see [Projects](projects.md#environment-variables)             |
| `GCP_LOCATION`                   | Tasks backend location fallback — see [Projects](projects.md#environment-variables)            |
| `GCP_SERVICE_ACCOUNT`            | Tasks backend service account fallback — see [Projects](projects.md#environment-variables)     |
