"""
This reroutes from an URL to a python view-function/class.

The main web/urls.py includes these routes for all urls (the root of the url)
so it can reroute to all website pages.

"""

from django.urls import path

from .views.mysheet import MySheetView
from .views.ansi_reference import AnsiReferenceView

from evennia.web.website.urls import urlpatterns as evennia_website_urlpatterns

# add patterns here
urlpatterns = [
    path("mysheet/", MySheetView.as_view(), name="my-sheet"),
    path("ansi/", AnsiReferenceView.as_view(), name="ansi-reference"),
]

# read by Django
urlpatterns = urlpatterns + evennia_website_urlpatterns
