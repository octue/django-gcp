# Reference: https://googleapis.dev/python/cloudtasks/latest/tasks_v2/cloud_tasks.html
from datetime import datetime, timedelta
from typing import Dict
import uuid

from google.api_core.exceptions import FailedPrecondition
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from . import exceptions
from .base import AppEngineBasedService, GoogleCloudPilotAPI


class CloudTasks(AppEngineBasedService, GoogleCloudPilotAPI):
    _client_class = tasks_v2.CloudTasksClient
    DEFAULT_METHOD = tasks_v2.HttpMethod.POST

    def _parent_path(self, project_id: str = None) -> str:
        return f"projects/{project_id or self.project_id}/locations/{self.location}"

    def _queue_path(self, queue: str, project_id: str = None) -> str:
        return self.client.queue_path(
            project=project_id or self.project_id,
            location=self.location,
            queue=queue,
        )

    def _task_path(self, task: str, queue: str, project_id: str = None) -> str:
        return self.client.task_path(
            project=project_id or self.project_id,
            location=self.location,
            queue=queue,
            task=task,
        )

    async def push(
        self,
        queue_name: str,
        url: str,
        payload: str = "",
        method: int = DEFAULT_METHOD,
        delay_in_seconds: int = 0,
        project_id: str = None,
        task_name: str = None,
        unique: bool = True,
        use_oidc_auth: bool = True,
        content_type: str = None,
        headers: Dict[str, str] = None,
    ) -> tasks_v2.Task:
        queue_path = self.client.queue_path(
            project=project_id or self.project_id,
            location=self.location,
            queue=queue_name,
        )
        if unique and task_name:
            task_name = f"{task_name}-{str(uuid.uuid4())}"

        task_path = (
            self.client.task_path(
                project=project_id or self.project_id,
                location=self.location,
                queue=queue_name,
                task=task_name,
            )
            if task_name
            else None
        )

        headers = headers or {}
        if content_type:
            headers["Content-Type"] = content_type

        task = tasks_v2.Task(
            name=task_path,
            http_request=tasks_v2.HttpRequest(
                http_method=method,
                url=url,
                body=payload.encode(),
                headers=headers,
                **(self.get_oidc_token(audience=url) if use_oidc_auth else {}),
            ),
        )

        if delay_in_seconds:
            target_date = datetime.utcnow() + timedelta(seconds=delay_in_seconds)
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(target_date)

            task.schedule_time = timestamp

        try:
            response = self.client.create_task(parent=queue_path, task=task)
        except FailedPrecondition as exc:
            if "a queue with this name existed recently" in exc.message:
                raise exceptions.DeletedRecently(resource=f"Queue {queue_name}") from exc
            if exc.message != "Queue does not exist.":
                raise

            self._create_queue(queue_name=queue_name, project_id=project_id)
            response = self.client.create_task(parent=queue_path, task=task)
        return response

    def _create_queue(
        self,
        queue_name: str,
        project_id: str = None,
    ) -> tasks_v2.Queue:
        parent = self._parent_path(project_id=project_id)
        queue_path = self._queue_path(queue=queue_name, project_id=project_id)

        queue = tasks_v2.Queue(
            name=queue_path,
        )
        return self.client.create_queue(
            parent=parent,
            queue=queue,
        )


__all__ = ("CloudTasks",)
