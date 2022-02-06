.. _authentication:

Authentication
==============

Authentication can be done by using Service Account Credentials or Application Default Credentials.

.. ATTENTION::
    At the time of writing, Google's process for managing authentication in their SDKs is an **absolute disgrace** in terms of how intractable it is, and how easy it is to leak credentials as a result.

    However, there are some promising developments currently happening (like *Workload Identify Federation* and *Service Account Impersonation*) so we hope that soon it'll be much easier to have a single workflow for this. In the meantime `it's worth following this guy <https://medium.com/datamindedbe/application-default-credentials-477879e31cb5>`_.

Create a service account
------------------------

In most cases, the default service accounts are not sufficient to read/write and sign files in GCS, so you will need to create a dedicated service account:

- Create a service account. (`Google Getting Started Guide <https://cloud.google.com/docs/authentication/getting-started>`__)

- Make sure your service account has access to the bucket and appropriate permissions. (`Using IAM Permissions <https://cloud.google.com/storage/docs/access-control/using-iam-permissions>`__)

On GCP infrastructure
---------------------

- This library will attempt to read the credentials provided when running on google cloud infrastructure.

- Ensure your service account is being used by the deployed GCR / GKE / GCE instance.

.. WARNING::
    Default Google Compute Engine (GCE) Service accounts are `unable to sign urls <https://googlecloudplatform.github.io/google-cloud-python/latest/storage/blobs.html#google.cloud.storage.blob.Blob.generate_signed_url>`_.


On GitHub Actions
-----------------

You may need to use the library on infrastructure external to Google like Github Actions - for example running ``collectstatic`` within a GitHub Actions release flow.

You'll want to avoid injecting a service account json file into your github actions if possible, so you should consider `Workload Identity Federation <https://cloud.google.com/blog/products/identity-security/enabling-keyless-authentication-from-github-actions>`_ which is made pretty easy by `these glorious github actions <https://github.com/google-github-actions>`_.

Locally
-------

We're working on using service account impersonation, but it's not fully available for all the SDKs yet, still a lot of teething problems (like `this one, solved 6 days ago at the time of writing<https://github.com/googleapis/google-auth-library-python/issues/762>`_.

So you should totally try that (please submit a PR here to show the process if you get it to work!!). In the meantime...

- Create the key and download `your-project-XXXXX.json` file.

.. DANGER::
    
    It's best not to store this in your project, to prevent accidentally committing it or building it into a docker image layer.
    Instead, bind monut it into docker images and devcontainers from somewhere else on your local system.

    If you must keep within your project, it's good practice to name the file ``gha-greds-<whatever>.json`` and make sure that ``gha-creds-*`` is in your ``.gitignore`` and ``.dockerignore`` files.

- If you're developing in a container (like a VSCode ``.devcontainer``), mount the file into the container. You can make gcloud available too - check out `this tutorial <https://medium.com/datamindedbe/application-default-credentials-477879e31cb5>`_.

- Set an environment variable of GOOGLE_APPLICATION_CREDENTIALS to the path of the json file.

