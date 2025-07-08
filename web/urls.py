from django.urls import include, path, re_path

# default evennia patterns
from evennia.web.urls import urlpatterns as evennia_default_urlpatterns

# add patterns
urlpatterns = [
    # website
    path("", include("web.website.urls")),
    # webclient
    path("webclient/", include("web.webclient.urls")),
    # web admin
    path("admin/", include("web.admin.urls")),
    # add any extra urls here:
    # path("mypath/", include("path.to.my.urls.file")),

]

# 'urlpatterns' must be named such for Django to find it.
urlpatterns = urlpatterns + evennia_default_urlpatterns
