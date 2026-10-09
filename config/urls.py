from django.conf import settings
from django.urls import include, path

urlpatterns = [
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns.append(path("_referencia/", include("core.urls_dev")))
