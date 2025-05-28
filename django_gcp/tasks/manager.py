import asyncio
import logging

from django.conf import settings

from django_gcp import exceptions

from . import tasks
from ._patch_cloud_scheduler import CloudScheduler
from ._pilot.pubsub import CloudSubscriber

logger = logging.getLogger(__name__)


# A note on the @property style of using django settings:
#
#   In many django libraries, it's commonplace to inspect and validate
#   the relevant django settings on start of the app, often adding them as
#   attributes to a controller or manager class like this TaskManager.
#
#   However, that's a much-misunderstood antipattern. The reason is that
#   in testing, the client app is instantiated on set up of the test, then
#   any variation in settings required for the test (i.e. applied with the
#   @override_settings decorator) is applied afterward... so while a
#   setting might change, any *copy* of it won't, so the test doesn't work.
#
#   There are two ways around this; either have a settings handler that
#   listens to the `setting_changed` signal, or directly access the relevant
#   setting each time. Here we do the latter (the storage module does the
#   former, as the storage settings are more complicated). By using
#   properties to get those settings, we have an easy access and a single
#   location where defaults are defined.


class TaskManager:
    """Manages and registers cloud tasks"""

    def __init__(self):
        self.on_demand_tasks = {}
        self.periodic_tasks = {}
        self.subscriber_tasks = {}

    @property
    def default_queue_name(self):
        """Return the GCP_TASKS_DEFAULT_QUEUE_NAME setting or a default"""
        return getattr(settings, "GCP_TASKS_DEFAULT_QUEUE_NAME")

    @property
    def delimiter(self):
        """Return the GCP_TASKS_DELIMITER setting or a default"""
        return getattr(settings, "GCP_TASKS_DELIMITER", "--")

    @property
    def disable_execute(self):
        """Return the GCP_TASKS_DISABLE_EXECUTE setting or default False"""
        return getattr(settings, "GCP_TASKS_DISABLE_EXECUTE", False)

    @property
    def domain(self):
        """Return the GCP_TASKS_DOMAIN setting or a default"""
        _domain = getattr(settings, "GCP_TASKS_DOMAIN")
        if not _domain.startswith("https://"):
            message = f"The GCP_TASKS_DOMAIN setting is invalid for use with a GCP PubSub push subscription. Endpoints need to be valid and secure (setting is: {_domain})."
            raise exceptions.InvalidEndpointError(message)
        return _domain

    @property
    def eager_execute(self):
        """Return the GCP_TASKS_EAGER_EXECUTE setting or a default"""
        return bool(getattr(settings, "GCP_TASKS_EAGER_EXECUTE", False))

    @property
    def region(self):
        """Return the GCP_TASKS_REGION setting or a default"""
        return getattr(settings, "GCP_TASKS_REGION", "europe-west1")

    @property
    def resource_affix(self):
        """Return the GCP_TASKS_RESOURCE_AFFIX setting or a default"""
        return getattr(settings, "GCP_TASKS_RESOURCE_AFFIX", None)

    def register_task(self, task_class):
        """Record the presence of a task class in this manager
        Allows iteration through different task classes for maintenance operations.
        """

        # TODO REFACTOR REQUEST There's ambiguity in what "register" means. Here, register means
        # "add to a dict where we record all the tasks" which is probably the correct one.
        # But, the Task class has a `register` method which has varying functionality depending on
        # how it is overloaded, and can mean "create something on google cloud". So it's necessary to
        # extract those meanings, and probably rename the method in Task(), e.g. to `create_resources`
        # or similar

        name = task_class.name()

        if not getattr(task_class, "abstract", False):
            if issubclass(task_class, tasks.SubscriberTask):
                logger.debug("Registering Subscriber Task %s", name)
                self.subscriber_tasks[name] = task_class

            elif issubclass(task_class, tasks.PeriodicTask):
                logger.debug("Registering Periodic Task %s", name)
                self.periodic_tasks[name] = task_class

            elif issubclass(task_class, tasks.OnDemandTask):
                logger.debug("Registering On Demand Task %s", name)
                self.on_demand_tasks[name] = task_class
        else:
            logger.debug("Skipping registration of Task %s (because the task class is abstract)", name)

    def create_scheduler_jobs(self, cleanup=False):
        """Create a scheduler jobs in GCP for each PeriodicTask

        Any existing scheduler jobs with the resource prefix will be removed

        """
        updated = []
        removed = []

        # TODO REFACTOR REQUEST In many places, 'scheduler jobs' (the actual name of the GCP resource)
        # are referred to as 'schedules' or similar. Collapse all terminology onto 'scheduler jobs'
        # so it's more intuitive to retermine what the resource is.

        # TODO REFACTOR REQUEST It doesn't make sense that the client usage is split between
        # here (for removing outdated scheduler jobs) and the task.schedule() method for creating
        # scheduler jobs. Either add a `clean_resources` class method to the task to do the cleanup
        # or move the creation code here.

        for _, task_klass in self.periodic_tasks.items():
            task = task_klass()
            task.schedule()
            updated.append(task.schedule_name)

        if cleanup:
            if self.resource_affix:
                logger.debug("Cleaning up unused Scheduler Jobs")
                client = CloudScheduler(location=self.region)
                for job in client.list(prefix=self.resource_affix):
                    schedule_name = job.name.split("/jobs/")[-1]
                    if schedule_name not in updated:
                        asyncio.run(client.delete(name=schedule_name))
                        removed.append(schedule_name)
            else:
                logger.warning(
                    "Cleanup of unused Scheduler Jobs was requested but skipped, because no resource affix was given - see the GCP_TASKS_RESOURCE_AFFIX docs for more details."
                )
        else:
            logger.debug("Skipping cleanup of unused Scheduler Jobs")

        return updated, removed

    def create_pubsub_subscriptions(self, cleanup=False):
        """Register all SubscriberTasks by creating push subscriptions for them on PubSub

        Any existing PubSub subscriptions with the resource prefix will be removed from PubSub.

        """
        updated = []
        removed = []

        # TODO REFACTOR REQUEST It doesn't make sense that the client usage is split between
        # here (for removing outdated subscriptions) and the task.register() method for creating
        # subscriptions. Either add a `clean_resources` class method to the task to do the cleanup
        # or move the creation code here.

        for task_name, task_klass in self.subscriber_tasks.items():
            task_klass().register()
            updated.append(task_name)

        async def _get_subscriptions():
            names = []
            async for subscription in client.list_subscriptions(prefix=self.resource_affix):
                susbcription_name = subscription.name.rsplit("subscriptions/", 1)[-1]
                task_name = subscription.push_config.push_endpoint.rsplit("/", 1)[-1]
                names.append((susbcription_name, task_name))
            return names

        if cleanup:
            if self.resource_affix:
                logger.debug("Cleaning up unused PubSub Subscriptions")
                client = CloudSubscriber()
                for subscription_id, subscribed_task in asyncio.run(_get_subscriptions()):
                    if subscribed_task not in updated:
                        asyncio.run(client.delete_subscription(subscription_id=subscription_id))
                        removed.append(subscribed_task)
            else:
                logger.warning(
                    "Cleanup of unused PubSub Subscriptions was requested but skipped, because no resource affix was given - see the GCP_TASKS_RESOURCE_AFFIX docs for more details."
                )

        else:
            logger.debug("Skipping cleanup of unused PubSub Subscriptions")

        return updated, removed
