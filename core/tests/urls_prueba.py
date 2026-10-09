"""URLconf solo para pruebas: agrega la referencia de desarrollo y una vista que falla."""

from django.urls import include, path


def vista_que_falla(request):
    raise RuntimeError("detalle interno que no debe llegar al usuario")


urlpatterns = [
    path("", include("core.urls")),
    path("_referencia/", include("core.urls_dev")),
    path("falla/", vista_que_falla),
]
