import datetime

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from django_gcp.workflows import WorkflowExecutionError

from .tasks import MyOnDemandTask
from .workflows import SampleWorkflow


@require_http_methods(["POST"])
def enqueue_an_on_demand_task(_):
    """A simple view, demonstrating how to enqueue an on-demand task from a view

    In production, you'll want to protect this behind a layer of authentication so only users with permission can trigger tasks :)

    """
    MyOnDemandTask().enqueue(a=1)

    # Usually, you'll want to return a 201 "Accepted for Processing" code... but the response is entirely up to you :)
    now = datetime.datetime.now()
    return JsonResponse({"enqueued_at": now.isoformat()}, status=201)


@require_http_methods(["GET", "POST"])
def workflow_tester(request):
    """View for testing workflow invocation and status checking."""
    context = {}

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "invoke":
            # Invoke the workflow
            try:
                duration = int(request.POST.get("duration", 5))
                should_fail = request.POST.get("should_fail") == "true"

                execution = SampleWorkflow().invoke(duration=duration, should_fail=should_fail)

                context["execution"] = {
                    "id": execution.id,
                    "name": execution.name,
                    "state": execution.state,
                    "start_time": execution.start_time.isoformat() if execution.start_time else None,
                    "console_url": SampleWorkflow().get_console_url(execution.id),
                }
                context["message"] = f"Workflow invoked successfully! Execution ID: {execution.id}"
                context["message_type"] = "success"

            except Exception as e:
                context["message"] = f"Error invoking workflow: {str(e)}"
                context["message_type"] = "error"

        elif action == "check_status":
            # Check workflow status
            try:
                execution_id = request.POST.get("execution_id")
                if not execution_id:
                    raise ValueError("Execution ID is required")

                status = SampleWorkflow().get_execution_status(execution_id)

                context["execution"] = {
                    "id": status.id,
                    "name": status.name,
                    "state": status.state,
                    "start_time": status.start_time.isoformat() if status.start_time else None,
                    "end_time": status.end_time.isoformat() if status.end_time else None,
                    "result": status.result,
                    "console_url": SampleWorkflow().get_console_url(status.id),
                }
                context["message"] = f"Status retrieved: {status.state}"
                context["message_type"] = "info"

            except WorkflowExecutionError as e:
                context["message"] = f"Error checking status: {str(e)}"
                context["message_type"] = "error"

    return render(request, "workflow_tester.html", context)
