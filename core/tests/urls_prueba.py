"""URLconf solo para pruebas: agrega la referencia de desarrollo y una vista que falla."""

from django.urls import include, path


def vista_que_falla(request):
    raise RuntimeError("detalle interno que no debe llegar al usuario")


urlpatterns = [
    path("", include("core.urls")),
    # La página 404 enlaza al inicio del sitio.
    path("", include("sitio.urls")),
    path("", include("solicitudes.urls")),
    path("", include("cuentas.urls")),
    path("_referencia/", include("core.urls_dev")),
    path("falla/", vista_que_falla),
]
