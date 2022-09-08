"""
ASGI config for bagchat project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter, ChannelNameRouter
from channels.security.websocket import AllowedHostsOriginValidator
import chat.routing
from chat.AuthMiddlewareToken import AuthMiddlewareToken
from base.views import EntryPointTasks
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bagchat.settings')
os.environ['ASGI_THREADS']="4"
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket":
        AllowedHostsOriginValidator(
        AuthMiddlewareToken(
            URLRouter(
                chat.routing.websocket_urlpatterns
            )
        )
    ),
    "channel": ChannelNameRouter({
        "channel-tasks": EntryPointTasks.as_asgi(),
    }),
})