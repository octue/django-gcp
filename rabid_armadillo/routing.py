from django.urls import path

from .consumers import MyConsumer


websocket_urlpatterns = [
    path(r"my-consumer/", MyConsumer.as_asgi()),
]
