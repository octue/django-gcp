# https://googleapis.dev/python/pubsub/latest/index.html
import base64
from dataclasses import dataclass
import json
from typing import Any, AsyncIterator, Callable, Dict, Union

from google.api_core.exceptions import AlreadyExists, NotFound
from google.cloud import pubsub_v1
from google.protobuf.field_mask_pb2 import FieldMask
from google.pubsub_v1 import PushConfig, Subscription, Topic, types

from .base import GoogleCloudPilotAPI


class CloudPublisher(GoogleCloudPilotAPI):
    _client_class = pubsub_v1.PublisherClient
    _service_name = "Cloud Pub/Sub"
    _google_managed_service = True

    async def create_topic(
        self,
        topic_id: str,
        project_id: str = None,
        exists_ok: bool = True,
        labels: Dict[str, str] = None,
    ) -> types.Topic:
        topic_path = self.client.topic_path(
            project=project_id or self.project_id,
            topic=topic_id,
        )
        topic_obj = types.Topic(
            name=topic_path,
            labels=labels,
        )
        try:
            topic = self.client.create_topic(
                request=topic_obj,
            )
        except AlreadyExists:
            if not exists_ok:
                raise
            topic = await self.get_topic(topic_id=topic_id, project_id=project_id)
        return topic

    async def update_topic(
        self,
        topic_id: str,
        project_id: str = None,
        labels: Dict[str, str] = None,
    ) -> types.Topic:
        topic_path = self.client.topic_path(
            project=project_id or self.project_id,
            topic=topic_id,
            labels=labels,
        )
        topic_obj = types.Topic(
            name=topic_path,
            labels=labels,
        )
        return self.client.update_topic(
            request=types.UpdateTopicRequest(
                topic=topic_obj,
                update_mask=FieldMask(paths=["labels"]),
            ),
        )

    async def get_topic(self, topic_id: str, project_id: str = None):
        topic_path = self.client.topic_path(
            project=project_id or self.project_id,
            topic=topic_id,
        )
        return self.client.get_topic(
            topic=topic_path,
        )

    async def list_topics(self, prefix: str = "", suffix: str = "", project_id: str = None) -> AsyncIterator[Topic]:
        project_path = self._project_path(project_id=project_id)
        topics = self.client.list_topics(
            project=project_path,
        )
        for topic in topics:
            name = topic.name.split("/topics/")[-1]
            if name.startswith(prefix) and name.endswith(suffix):
                yield topic

    async def publish(
        self,
        message: str,
        topic_id: str,
        project_id: str = None,
        attributes: Dict[str, Any] = None,
    ) -> types.PublishResponse:
        topic_path = self.client.topic_path(
            project=project_id or self.project_id,
            topic=topic_id,
        )
        try:
            future = self.client.publish(
                topic=topic_path,
                data=message.encode(),
                **(attributes or {}),
            )
            return future.result()
        except NotFound:
            await self.create_topic(
                topic_id=topic_id,
                project_id=project_id,
            )
            future = self.client.publish(
                topic=topic_path,
                data=message.encode(),
                **(attributes or {}),
            )
            return future.result()


class CloudSubscriber(GoogleCloudPilotAPI):
    _client_class = pubsub_v1.SubscriberClient
    _service_name = "Cloud Pub/Sub"
    _google_managed_service = True

    async def list_subscriptions(
        self,
        prefix: str = "",
        suffix: str = "",
        project_id: str = None,
    ) -> AsyncIterator[Subscription]:
        all_subscriptions = self.client.list_subscriptions(
            project=f"projects/{project_id or self.project_id}",
        )
        for subscription in all_subscriptions:
            name = subscription.name.split("/subscriptions/")[-1]
            if name.startswith(prefix) and name.endswith(suffix):
                yield subscription

    async def get_subscription(self, subscription_id: str, project_id: str = None) -> Subscription:
        subscription_path = self.client.subscription_path(
            project=project_id or self.project_id,
            subscription=subscription_id,
        )

        return self.client.get_subscription(
            subscription=subscription_path,
        )

    async def delete_subscription(self, subscription_id: str, project_id: str = None) -> None:
        subscription_path = self.client.subscription_path(
            project=project_id or self.project_id,
            subscription=subscription_id,
        )

        return self.client.delete_subscription(
            subscription=subscription_path,
        )

    async def create_subscription(
        self,
        topic_id: str,
        subscription_id: str,
        project_id: str = None,
        exists_ok: bool = True,
        auto_create_topic: bool = True,
        enable_message_ordering: bool = False,
        push_to_url: str = None,
        use_oidc_auth: bool = False,
    ) -> Subscription:
        topic_path = self.client.topic_path(
            project=project_id or self.project_id,
            topic=topic_id,
        )
        subscription_path = self.client.subscription_path(
            project=project_id or self.project_id,
            subscription=subscription_id,
        )

        push_config = None
        if push_to_url:
            push_config = PushConfig(
                push_endpoint=push_to_url,
                **(self.get_oidc_token(audience=push_to_url) if use_oidc_auth else {}),
            )

        subscription = Subscription(
            name=subscription_path,
            topic=topic_path,
            push_config=push_config,
            enable_message_ordering=enable_message_ordering,
        )

        try:
            return self.client.create_subscription(request=subscription)
        except NotFound:
            if not auto_create_topic:
                raise
            await CloudPublisher().create_topic(
                topic_id=topic_id,
                project_id=project_id,
                exists_ok=False,
            )
            return self.client.create_subscription(request=subscription)
        except AlreadyExists:
            if not exists_ok:
                raise
            return await self.get_subscription(subscription_id=subscription_id, project_id=project_id)

    async def update_subscription(
        self,
        topic_id: str,
        subscription_id: str,
        project_id: str = None,
        push_to_url: str = None,
        use_oidc_auth: bool = False,
    ) -> Subscription:
        topic_path = self.client.topic_path(
            project=project_id or self.project_id,
            topic=topic_id,
        )
        subscription_path = self.client.subscription_path(
            project=project_id or self.project_id,
            subscription=subscription_id,
        )

        push_config = None
        if push_to_url:
            push_config = PushConfig(
                push_endpoint=push_to_url,
                **(self.get_oidc_token(audience=push_to_url) if use_oidc_auth else {}),
            )

        subscription = Subscription(
            name=subscription_path,
            topic=topic_path,
            push_config=push_config,
        )

        update_mask = {"paths": {"push_config"}}

        return self.client.update_subscription(request={"subscription": subscription, "update_mask": update_mask})

    async def create_or_update_subscription(
        self,
        topic_id: str,
        subscription_id: str,
        project_id: str = None,
        auto_create_topic: bool = True,
        enable_message_ordering: bool = False,
        push_to_url: str = None,
        use_oidc_auth: bool = False,
    ) -> Subscription:
        try:
            return await self.create_subscription(
                topic_id=topic_id,
                subscription_id=subscription_id,
                project_id=project_id,
                exists_ok=False,
                auto_create_topic=auto_create_topic,
                enable_message_ordering=enable_message_ordering,
                push_to_url=push_to_url,
                use_oidc_auth=use_oidc_auth,
            )
        except AlreadyExists:
            return await self.update_subscription(
                topic_id=topic_id,
                subscription_id=subscription_id,
                project_id=project_id,
                push_to_url=push_to_url,
                use_oidc_auth=use_oidc_auth,
            )

    async def subscribe(self, topic_id: str, subscription_id: str, callback: Callable, project_id: str = None):
        await self.create_subscription(
            topic_id=topic_id,
            subscription_id=subscription_id,
            project_id=project_id,
        )

        subscription_path = self.client.subscription_path(
            project=project_id or self.project_id,
            subscription=subscription_id,
        )
        future = self.client.subscribe(
            subscription=subscription_path,
            callback=callback,
        )
        future.result()


@dataclass
class Message:
    id: str
    data: Any
    attributes: Dict[str, Any]
    subscription: str

    @classmethod
    def load(cls, body: Union[str, bytes, Dict], parser: Callable = json.loads) -> "Message":
        # https://cloud.google.com/pubsub/docs/push#receiving_messages
        if isinstance(body, bytes):
            body = body.decode()
        if isinstance(body, str):
            body = json.loads(body)

        return Message(
            id=body["message"]["messageId"],
            attributes=body["message"]["attributes"],
            subscription=body["subscription"],
            data=parser(base64.b64decode(body["message"]["data"]).decode("utf-8")),
        )


__all__ = (
    "CloudPublisher",
    "CloudSubscriber",
    "Message",
)
