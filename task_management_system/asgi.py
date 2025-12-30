import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
import boards.routing     

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "task_management_system.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(boards.routing.websocket_urlpatterns)
    ),
})