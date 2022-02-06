.. _projects:

Projects
========

In most cases, the id of the GCP project you're working on will be inferred from your
Application Default Credentials or Service Account (see :ref:`authentication`).

If that's not correct (eg your service account has privileges across projects), you may need
to set it explicitly.

Settings
--------

``GCP_PROJECT_ID`` (optional)

Your Google Cloud project ID. If unset, falls back to the default
inferred from the environment.
