.. _tasks_workers:

Task Workers
============

A *worker* is a server instance, running the django application, whose sole job it is to do the tasks
that get placed onto the queue (or pushed via scheduler or PubSub).

.. _deploying_workers:

Deploying Workers
-----------------

In the most straightforward usage, *you don't even need a separate worker*. To get up and running minimally, you can point
:ref:`gcp_tasks_domain` straight back to the app itself! Check the docs of that setting for more tips on local development.

However, in most cases you'll want the server to scale independently of the worker service and that's not hard to achieve.

* Begin using exactly the same configuration and deployment process that you use for the main server (eg deploy to Cloud Run, but use a `-worker` suffix in the app name).
* Get the release-specific URL to that deployment.
* Set that URL as the :ref:`gcp_tasks_domain` value on the server.


.. TIP::
    Using Cloud Run, you can provide a tag to create a *revision-specific* URL as part of the worker deployment process.
    If you deploy worker and server at the same time, and configure the server with the revision-specific URL, the server will
    always send tasks to the *same version of code* that it's running on itself. This is great for maintaining continuous
    uptime without worrying about breaking changes in the data required by your tasks.

    On GitHub Actions, that looks something like:

    .. code-block:: yaml

       # ... build an image, then ...

       - name: Deploy to Cloud Run Worker
         id: deploy_worker
         uses: google-github-actions/deploy-cloudrun@v0
         with:
           service: yourapp-worker-${{ needs.build.outputs.environment }}
           image: ${{ needs.build.outputs.image_version_artefact }}
           region: europe-west1
           tag: ${{ needs.build.outputs.short_sha }}

       - name: Deploy to Cloud Run Server
         id: deploy_server
         uses: google-github-actions/deploy-cloudrun@v0
         with:
           env_vars: |
             GCP_TASKS_DOMAIN=${{ steps.deploy_worker.outputs.url }}
           image: ${{ needs.build.outputs.image_version_artefact }}
           region: europe-west1
           service: yourapp-server-${{ needs.build.outputs.environment }}
           tag: ${{ needs.build.outputs.short_sha }}


.. _microservices_as_workers:

Microservices as Workers
------------------------

There's nothing special or django-gcp specific about the data passed to tasks.
So, there's absolutely no reason why you shouldn't use entirely separate
microservices to receive and process tasks created by ``django-gcp``!

Enjoy yourself, and let us know what you build :)
