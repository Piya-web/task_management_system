from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/boards/(?P<board_id>\w+)/$", consumers.BoardConsumer.as_asgi()),
    re_path(r"ws/notifications/(?P<user_id>\w+)/$", consumers.NotificationConsumer.as_asgi()),
]