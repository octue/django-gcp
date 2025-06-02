from django.urls import path

from django_gcp.events.views import GoogleCloudEventsView
from django_gcp.tasks.views import GoogleCloudSubscriberTaskView, GoogleCloudTaskView

urlpatterns = [
    path(r"events/<event_kind>/<event_reference>", GoogleCloudEventsView.as_view(), name="gcp-events"),
    path(r"subscriber-tasks/<task_name>", GoogleCloudSubscriberTaskView.as_view(), name="gcp-subscriber-tasks"),
    path(r"tasks/<task_name>", GoogleCloudTaskView.as_view(), name="gcp-tasks"),
]
