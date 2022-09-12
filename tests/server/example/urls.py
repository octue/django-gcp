from django.urls import re_path

from .views import enqueue_an_on_demand_task


urlpatterns = [
    re_path(r"^enqueue-an-on-demand-task/", enqueue_an_on_demand_task, name="enqueue-on-demand"),
]
