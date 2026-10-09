from django.urls import path

from core import referencia

app_name = "referencia"

urlpatterns = [
    path("componentes/", referencia.componentes, name="componentes"),
    path("404/", referencia.error_404, name="error_404"),
    path("500/", referencia.error_500, name="error_500"),
]
