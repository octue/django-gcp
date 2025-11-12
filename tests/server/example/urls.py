from django.urls import re_path

from .views import enqueue_an_on_demand_task, workflow_tester

urlpatterns = [
    re_path(r"^enqueue-an-on-demand-task/", enqueue_an_on_demand_task, name="enqueue-on-demand"),
    re_path(r"^workflow-tester/", workflow_tester, name="workflow-tester"),
]
