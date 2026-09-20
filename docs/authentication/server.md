# Authenticating the server

Authenticating the server requires Service Account Credentials or Application Default
Credentials (ADCs).

!!! warning

    Google's process for managing authentication across its SDKs is somewhat intractable, with
    difficult-to-navigate guidance and varying practices recommended across the platform. It is
    very easy to leak credentials as a result, so please take care.

    There are promising developments (like *Workload Identity Federation* and *Service Account
    Impersonation*), so we hope a single workflow for this will soon be practical. In the
    meantime, [this article on Application Default Credentials](https://medium.com/datamindedbe/application-default-credentials-477879e31cb5)
    is worth reading.

    A particular issue for storage is the need to sign files in GCS. Signing either requires a
    dedicated service account with the full key available (no longer recommended by Google), or
    requires additional calls to a Google-hosted API, significantly slowing any interaction that
    uses signed URLs.

    If you are not using media storage — only tasks, events, and static (public) storage — this
    is not an issue, and you can use service account impersonation, federation, or ADCs as
    appropriate.

## Create a service account

In most cases the default service accounts are not sufficient to read, write, and sign files in
GCS, so you will need to create a dedicated service account:

- Create a service account ([Google's getting started guide](https://cloud.google.com/docs/authentication/getting-started)).
- Make sure the service account has access to the bucket and appropriate permissions
  ([using IAM permissions](https://cloud.google.com/storage/docs/access-control/using-iam-permissions)).

## On GCP infrastructure

The library will attempt to read the credentials provided when running on Google Cloud
infrastructure. Ensure your service account is the one used by the deployed Cloud Run, GKE, or
GCE instance.

!!! warning

    Default Google Compute Engine (GCE) service accounts are
    [unable to sign URLs](https://googlecloudplatform.github.io/google-cloud-python/latest/storage/blobs.html#google.cloud.storage.blob.Blob.generate_signed_url).

## On GitHub Actions

You may need to use the library on infrastructure external to Google, for example running
`collectstatic` within a GitHub Actions release flow.

Avoid injecting a service account JSON file into your GitHub Actions if possible. Instead,
consider [Workload Identity Federation](https://cloud.google.com/blog/products/identity-security/enabling-keyless-authentication-from-github-actions),
which is made straightforward by [Google's official GitHub Actions](https://github.com/google-github-actions).

## Locally

Service account impersonation is the eventual aim for local development, but it is not yet fully
supported across all the SDKs. In the meantime:

- Create a service account key and download the `your-project-XXXXX.json` file.
- If you are developing in a container (like a VS Code devcontainer), mount the file into the
  container. You can make `gcloud` available too — see
  [this tutorial](https://medium.com/datamindedbe/application-default-credentials-477879e31cb5).
- Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the path of the JSON file.

!!! danger

    It is best not to store the key file in your project at all, to prevent accidentally
    committing it or building it into a Docker image layer. Instead, bind-mount it into Docker
    images and devcontainers from somewhere else on your local system.

    If you must keep it within your project, name the file `gha-creds-<whatever>.json` and make
    sure that `gha-creds-*` is in your `.gitignore` and `.dockerignore` files.
