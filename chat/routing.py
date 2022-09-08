from chat import consumers
from django.urls import re_path, path
websocket_urlpatterns = [
    path('ws/bags/chat/sync/', consumers.BeginMessageConsumer.as_asgi())
]