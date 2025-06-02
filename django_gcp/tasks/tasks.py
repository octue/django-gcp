# Disabled while refactoring:
# pylint: disable=missing-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=no-member
from abc import abstractmethod
from datetime import datetime, timedelta
import hashlib
import logging

from django.apps import apps
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.utils.timezone import now
from google.api_core.exceptions import AlreadyExists
from google.cloud import pubsub_v1

from django_gcp.events.utils import decode_pubsub_message
from django_gcp.exceptions import DuplicateTaskError, IncompatibleSettingsError, IncorrectTaskUsageError

from ._patch_cloud_scheduler import CloudScheduler
from ._patch_cloud_tasks import CloudTasks
from ._pilot.pubsub import CloudPublisher, CloudSubscriber
from .helpers import run_coroutine
from .serializers import deserialize, serialize

logger = logging.getLogger(__name__)


def apply_resource_affix(value, suffix=False):
    manager = apps.get_app_config("django_gcp").task_manager
    if manager.resource_affix is not None:
        if suffix:
            return f"{value}{manager.delimiter}{manager.resource_affix}"
        else:
            return f"{manager.resource_affix}{manager.delimiter}{value}"

    return value


def apply_prefix(value):
    return apply_resource_affix(value, suffix=False)


def apply_suffix(value):
    return apply_resource_affix(value, suffix=True)


def short_sha(value, digits=8):
    """Calculate a short sha from an input string, with a certain degree of uniqueness"""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:digits]


class TaskMeta(type):
    """Metadata class representing a Task"""

    def __new__(cls, name, bases, attrs):
        """On creation of a new Task subclass, register it with the task manager for the django-gcp app"""
        klass = type.__new__(cls, name, bases, attrs)

        # TODO Simplify this statement, what on earth is its purpose?
        #      If the class has attr abstract=True but abstract not in attrs set abstract=False?? WTF??
        if getattr(klass, "abstract", False) and "abstract" not in attrs:
            setattr(klass, "abstract", False)

        if klass.__name__ not in ["Task", "OnDemandTask", "PeriodicTask", "SubscriberTask"]:
            apps.get_app_config("django_gcp").task_manager.register_task(task_class=klass)

        return klass

    def __call__(cls, *args, **kwargs):
        """Override a task's __call__ method to check that it's been appropriately subclassed
        This catches the most common usage error.
        """
        if cls.__name__ in ["Task", "OnDemandTask", "PeriodicTask", "SubscriberTask"]:
            raise IncorrectTaskUsageError(f"Do not instantiate a {cls.__name__}. Inherit and create your own.")

        return super().__call__(*args, **kwargs)


class Task(metaclass=TaskMeta):
    """Task base class"""

    _url_name = "gcp-tasks"
    deduplicate = False

    def enqueue(self, **kwargs):
        """Invoke a task (place it onto a queue for processing)

        Some settings affect the behaviour of this method, allowing bypass or immediate execution. See settings documentation for more.
        """
        return self._send(
            task_kwargs=kwargs,
        )

    def enqueue_later(self, when, **kwargs):
        """Invoke a task (place it onto a queue for processing after some time delay)

        Some settings affect the behaviour of this method, allowing bypass or immediate execution. See settings documentation for more.
        """
        if isinstance(when, int):
            delay_in_seconds = when
        elif isinstance(when, timedelta):
            delay_in_seconds = when.total_seconds()
        elif isinstance(when, datetime):
            delay_in_seconds = (when - now()).total_seconds()
        else:
            raise ValueError(f"Unsupported schedule {when} of type {when.__class__.__name__}")

        return self._send(
            task_kwargs=kwargs,
            api_kwargs=dict(delay_in_seconds=delay_in_seconds),
        )

    def execute(self, request_body):
        """Deserialises the received request and calls the run() method"""
        try:
            task_kwargs = self._body_to_kwargs(request_body=request_body)
        except Exception as e:
            logger.warning(e, exc_info=True)
            return f"Unable to parse request arguments. Error was: {e}", 400

        try:
            return self.run(**task_kwargs), 200
        except Exception as e:
            logger.error(e, exc_info=True)
            return "Error running task", 500

    @property
    def manager(self):
        """The task manager instance used to record registered apps"""
        return apps.get_app_config("django_gcp").task_manager

    @classmethod
    def name(cls):
        """Name of the task class"""
        return cls.__name__

    @property
    def queue_name(self):
        """Name of the queue that tasks will be placed on
        Override to use a different queue for different task subclasses
        """
        return self.manager.default_queue_name

    @property
    def slug(self):
        """Slugified name of this class"""
        return slugify(self.name())

    @abstractmethod
    def run(self, **kwargs):
        raise NotImplementedError()

    @classmethod
    def url(cls):
        domain = apps.get_app_config("django_gcp").task_manager.domain
        path = reverse(cls._url_name, args=(cls.name(),))
        return f"{domain}{path}"

    def _body_to_kwargs(self, request_body):
        data = deserialize(request_body)
        return data

    # TODO REFACTOR REQUEST The base `Task` class seems to deal with on-demand tasks
    # (using Cloud Tasks) then is inherited by other classes using different task
    # mechanisms (e.g. Cloud Scheduler and Pub/Sub).
    # The Task class is thus treated only partly as an ABC.
    # We should refactor Task to split it into two; a true ABC containing only
    # common functionality, and an OnDemandTask class which implements the detail of
    # interacting with Cloud Tasks, like the following _send method

    def _send(self, task_kwargs, api_kwargs=None):
        if self.manager.disable_execute and self.manager.eager_execute:
            raise IncompatibleSettingsError("disable_execute and eager_execute should be mutually exclusive")

        if self.manager.disable_execute:
            return None

        payload = serialize(task_kwargs)
        if self.manager.eager_execute:
            return self.run(**deserialize(payload))

        api_kwargs = api_kwargs or {}
        api_kwargs.update(
            dict(
                queue_name=self.queue_name,
                url=self.url(),
                payload=payload,
            )
        )

        if self.deduplicate:
            # NOTE:
            #   If deduplicating tasks, a task ID must be supplied. As noted here in the GCP docs,
            #   this creates significant additional latency into the task allocation. Efficient
            #   operation of the task queue demands a binomially distributed task ID, meaning
            #   that we don't want to be adding a uniform resource prefix; so we use a suffix instead.
            #   The short sha prefix is used to "uniquely" (within reason) identify payloads, meaning you
            #   can trigger the same task repeatedly with different payloads, but attempting to repeat a
            #   task with the same payload will fail for ~1hour after the original task was deleted or
            #   executed.
            unique_task_name = apply_suffix(f"{short_sha(payload)}{self.manager.delimiter}{self.slug}")
            api_kwargs.update(
                dict(
                    task_name=unique_task_name,
                    unique=False,
                )
            )

            try:
                return run_coroutine(handler=self.__client.push, **api_kwargs)
            except AlreadyExists as e:
                raise DuplicateTaskError(
                    "Duplicate task detected (task already exists with this name and payload sha). You can trigger the same task repeatedly with different payloads, but attempting to repeat a task with the same payload will fail for ~1hour after the original task was deleted or executed."
                ) from e
        else:
            return run_coroutine(handler=self.__client.push, **api_kwargs)

    @property
    def __client(self):
        return CloudTasks(location=self.manager.region)


class OnDemandTask(Task):
    """Inherit from here to enable on-demand tasks

    This class is empty right now, but is here to avoid a breaking change later when we refactor
    the Task class. You should inherit from this.

    """

    abstract = True

    # TODO refactor the functionality specific to on-demand tasks to here from the Task class, because
    #  currently the Task class functions both as a base and as a specific variant class.

    @abstractmethod
    def run(self, **kwargs):
        raise NotImplementedError()


class PeriodicTask(Task):
    run_every = None

    @abstractmethod
    def run(self, **kwargs):
        raise NotImplementedError()

    def schedule(self, **kwargs):
        payload = serialize(kwargs)

        if self.manager.eager_execute:
            return self.run(**deserialize(payload))

        return run_coroutine(
            handler=self.__client.put,
            name=self.schedule_name,
            url=self.url(),
            payload=payload,
            cron=self.run_every,
        )

    @property
    def schedule_name(self):
        return apply_prefix(self.slug)

    @property
    def __client(self):
        return CloudScheduler(location=self.manager.region)


class SubscriberTask(Task):
    abstract = True
    _use_oidc_auth = True
    _url_name = "gcp-subscriber-tasks"
    enable_message_ordering = False

    def publish(self, data, attributes=None):
        """Publish a message onto the PubSub topic that this subscriber listens to

        This is mostly a convenience method for running integration tests, it's not
        intended for general use (What would be the point of sending a message to
        yourself? It's possible to use Pub/Sub as a tasks queue this way but that
        doesn't seem like it'd ever be useful compared to using the purpose-built
        cloud tasks queue).

        """
        return run_coroutine(
            handler=self.__publisher_client.publish,
            message=serialize(data),
            topic_id=self.topic_id,
            attributes=attributes,
        )

    def register(self):
        return run_coroutine(
            handler=self.__client.create_or_update_subscription,
            topic_id=self.topic_id,
            subscription_id=self.subscription_id,
            enable_message_ordering=self.enable_message_ordering,
            push_to_url=self.url(),
            use_oidc_auth=self._use_oidc_auth,
        )

    @abstractmethod
    def run(self, data, attributes, message_id, ordering_key, publish_time, subscription, **kwargs):  # pylint: disable=arguments-differ
        raise NotImplementedError()

    @property
    def subscription_id(self):
        return apply_prefix(f"{self.topic_id}{self.manager.delimiter}{self.slug}")

    @property
    @abstractmethod
    def topic_id(self):
        raise NotImplementedError()

    def _body_to_kwargs(self, request_body):
        return decode_pubsub_message(request_body)

    @property
    def __client(self):
        return CloudSubscriber()

    @property
    def __publisher_client(self):
        publisher_options = pubsub_v1.types.PublisherOptions(
            enable_message_ordering=self.enable_message_ordering,
        )
        return CloudPublisher(publisher_options=publisher_options)
