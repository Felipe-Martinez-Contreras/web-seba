from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("core.urls")),
    path("", include("cuentas.urls")),
    path("portal/", include("portal.urls")),
    path("panel/", include("panel.urls")),
]

# El admin de Django es solo para el superusuario técnico (ADM-12): su ruta sale de una
# variable de entorno y, si no está definida, no se publica.
if settings.DJANGO_ADMIN_RUTA:
    urlpatterns.append(path(f"{settings.DJANGO_ADMIN_RUTA}/", admin.site.urls))

if settings.DEBUG:
    urlpatterns.append(path("_referencia/", include("core.urls_dev")))
