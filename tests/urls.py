from django.http import HttpResponse
from django.urls import include, path


def ok(request):
	return HttpResponse("ok")


webclient_patterns = ([path("", ok, name="index")], "webclient")

urlpatterns = [
	path("roomeditor/", include("roomeditor.urls")),
	path("webclient/", include(webclient_patterns, namespace="webclient")),
	path("help/", ok, name="help"),
]
