# Task workers

A _worker_ is a server instance, running the Django application, whose sole job is to execute
the tasks placed on the queue (or pushed via Scheduler or Pub/Sub).

## Deploying workers

In the most straightforward usage, _you do not even need a separate worker_. To get up and
running minimally, you can point [`GCP_TASKS_DOMAIN`](settings.md#gcp_tasks_domain) straight
back at the app itself. Check that setting's documentation for tips on local development, too.

However, in most cases you will want the server to scale independently of the worker service,
and that is not hard to achieve:

1. Deploy the worker using exactly the same configuration and deployment process as the main
   server (for example, deploy to Cloud Run, but use a `-worker` suffix in the app name).
2. Get the URL of that deployment.
3. Set that URL as the [`GCP_TASKS_DOMAIN`](settings.md#gcp_tasks_domain) value on the server.

!!! tip

    Using Cloud Run, you can provide a tag to create a *revision-specific* URL as part of the
    worker deployment process. If you deploy worker and server at the same time, and configure
    the server with the revision-specific URL, the server will always send tasks to the *same
    version of code* that it is running itself. This is great for maintaining continuous
    uptime without worrying about breaking changes in the data required by your tasks.

    On GitHub Actions, that looks something like:

    ```yaml
    # ... build an image, then ...

    - name: Deploy to Cloud Run Worker
      id: deploy_worker
      uses: google-github-actions/deploy-cloudrun@v2
      with:
        service: yourapp-worker-${{ needs.build.outputs.environment }}
        image: ${{ needs.build.outputs.image_version_artefact }}
        region: europe-west1
        tag: ${{ needs.build.outputs.short_sha }}

    - name: Deploy to Cloud Run Server
      id: deploy_server
      uses: google-github-actions/deploy-cloudrun@v2
      with:
        env_vars: |
          GCP_TASKS_DOMAIN=${{ steps.deploy_worker.outputs.url }}
        image: ${{ needs.build.outputs.image_version_artefact }}
        region: europe-west1
        service: yourapp-server-${{ needs.build.outputs.environment }}
        tag: ${{ needs.build.outputs.short_sha }}
    ```

## Microservices as workers

There is nothing special or `django-gcp`-specific about the data passed to tasks, so there is
absolutely no reason why you should not use entirely separate microservices to receive and
process tasks created by `django-gcp`.

Enjoy yourself, and let us know what you build!
