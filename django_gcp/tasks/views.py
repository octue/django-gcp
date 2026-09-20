import json
import logging
from typing import Any, Dict

from django.apps import apps
from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from django_gcp.auth import OIDCAuthRequiredMixin

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class GoogleCloudTaskView(OIDCAuthRequiredMixin, View):
    """Endpoints for on-demand and periodic tasks

    Callers must present a valid OIDC identity token from a service account listed in
    ``GCP_TASKS_INVOKER_SERVICE_ACCOUNT_EMAILS`` (falling back to
    ``GCP_INVOKER_SERVICE_ACCOUNT_EMAILS``), unless ``GCP_TASKS_DISABLE_AUTH`` is True or the
    view is wired with ``as_view(auth_required=False)``.
    """

    invoker_emails_settings = ("GCP_TASKS_INVOKER_SERVICE_ACCOUNT_EMAILS", "GCP_INVOKER_SERVICE_ACCOUNT_EMAILS")
    disable_auth_setting = "GCP_TASKS_DISABLE_AUTH"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tasks = self._get_available_tasks()

    def _get_available_tasks(self):
        task_manager = apps.get_app_config("django_gcp").task_manager
        all_tasks = task_manager.on_demand_tasks.copy()
        all_tasks.update(task_manager.periodic_tasks.copy())
        return all_tasks

    def post(self, request, task_name, *args, **kwargs):
        """Receive POST request containing task data and execute the task"""
        try:
            task_class = self.tasks[task_name]
        except KeyError:
            result = {"error": f"Task {task_name} not found"}
            # Listing the registered tasks to an unknown caller is an information leak
            if getattr(settings, "DEBUG", False):
                result["available_tasks"] = list(self.tasks)
            return self._prepare_response(status=404, payload=result)

        task = task_class()
        try:
            task_kwargs = task._body_to_kwargs(request_body=request.body)
        except Exception as e:
            logger.warning(e, exc_info=True)
            return self._prepare_response(
                status=400, payload={"error": f"Unable to parse request arguments. Error was: {e}"}
            )

        try:
            result = task.execute(**task_kwargs)
        except Exception as e:
            logger.error(e, exc_info=True)
            return self._prepare_response(status=500, payload={"error": f"Error running task. Error was: {e}"})

        return self._prepare_response(status=200, payload={"result": result})

    def _prepare_response(self, status: int, payload: Dict[str, Any]):
        return HttpResponse(status=status, content=json.dumps(payload), content_type="application/json")


class GoogleCloudSubscriberTaskView(GoogleCloudTaskView):
    """Endpoints for subscriber tasks"""

    def _get_available_tasks(self):
        return apps.get_app_config("django_gcp").task_manager.subscriber_tasks.copy()
