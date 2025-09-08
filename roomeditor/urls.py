# Tabs are intentional.
from django.urls import path

from . import views

app_name = "roomeditor"
urlpatterns = [
	path("rooms/", views.room_list, name="room-list"),
	path("room/new/", views.room_new, name="room_new"),
	path("room/<int:pk>/", views.room_edit, name="room_edit"),
	path("room/<int:pk>/delete/", views.room_delete, name="room_delete"),
	path("exit/new/<int:room_pk>/", views.exit_new, name="exit_new"),
	path("exit/<int:pk>/edit/", views.exit_edit, name="exit_edit"),
	path("exit/<int:pk>/delete/", views.exit_delete, name="exit_delete"),
	path("ansi/preview/", views.ansi_preview, name="ansi_preview"),
	path("api/rooms/", views.room_search_api, name="room_search_api"),
]
