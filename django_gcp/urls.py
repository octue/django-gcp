from django.urls import path
from django_gcp.events.views import GoogleCloudEventsView


# from django_gcp.tasks import views as tasks_views


urlpatterns = [
    # path(r"tasks/<task_name>", tasks_views.GoogleCloudTaskView.as_view(), name="gcp-tasks"),
    # path(r"subscriptions/<task_name>", tasks_views.GoogleCloudSubscribeView.as_view(), name="gcp-task-subscriptions"),
    path(r"events/<event_kind>/<event_reference>", GoogleCloudEventsView.as_view(), name="gcp-events"),
]
