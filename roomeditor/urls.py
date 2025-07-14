from django.urls import path
from . import views

app_name = "roomeditor"

urlpatterns = [
    path("", views.room_list, name="room-list"),
    path("new/", views.room_edit, name="room-create"),
    path("<int:room_id>/", views.room_edit, name="room-edit"),
    path(
        "<int:room_id>/delete_exit/<int:exit_id>/",
        views.delete_exit,
        name="delete-exit",
    ),
    path(
        "<int:room_id>/edit_exit/<int:exit_id>/",
        views.edit_exit,
        name="edit-exit",
    ),
]
