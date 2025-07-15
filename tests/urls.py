from django.urls import include, path

urlpatterns = [
    path("roomeditor/", include("roomeditor.urls")),
]
