# Environment variables

This page indexes configuration that `django-gcp` reads from the process environment rather
than from Django settings. Settings read from your Django configuration are indexed in
[Django settings](django-settings.md).

## Authentication

| Variable                         | Details                                                                                           |
| -------------------------------- | ------------------------------------------------------------------------------------------------- |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to a credentials file — see [Authenticating the server](../authentication/server.md#locally) |

## Tasks

The tasks backend resolves its project, location, and service account from the environment
when they cannot be determined another way; see
[Tasks settings — environment variables](../services/tasks/settings.md#environment-variables)
for the resolution order.

| Variable              | Details                                                                                                      |
| --------------------- | ------------------------------------------------------------------------------------------------------------ |
| `GCP_PROJECT`         | Project in which task queues, scheduler jobs, and subscriptions are managed                                  |
| `GCP_LOCATION`        | Location for those resources (see also [`GCP_TASKS_REGION`](../services/tasks/settings.md#gcp_tasks_region)) |
| `GCP_SERVICE_ACCOUNT` | Service account used by the tasks backend                                                                    |
