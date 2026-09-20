# Projects

In most cases, the ID of the GCP project you are working on will be inferred from your
Application Default Credentials or Service Account (see
[Authentication](authentication/index.md)).

If that is not correct (for example, your service account has privileges across projects),
you may need to set it explicitly.

## Settings

### `GCP_PROJECT_ID`

Type: `string` (optional)

Your Google Cloud project ID. If unset, falls back to the default inferred from the
environment.
