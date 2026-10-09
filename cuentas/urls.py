from django.urls import path

from cuentas import views
from cuentas.models import EnlaceAcceso

app_name = "cuentas"

urlpatterns = [
    path("acceso/", views.acceso, name="acceso"),
    path("acceso/verificacion/", views.verificacion, name="verificacion"),
    path("acceso/2fa/configurar/", views.configurar_2fa, name="configurar_2fa"),
    path("acceso/2fa/codigos/", views.codigos_2fa, name="codigos_2fa"),
    path("salir/", views.salir, name="salir"),
    path("recuperar/", views.recuperar, name="recuperar"),
    path("recuperar/enviado/", views.recuperar_enviado, name="recuperar_enviado"),
    path(
        "activar/<str:token>/",
        views.definir_contrasena,
        {"tipo": EnlaceAcceso.Tipo.ACTIVACION},
        name="activar",
    ),
    path(
        "restablecer/<str:token>/",
        views.definir_contrasena,
        {"tipo": EnlaceAcceso.Tipo.RESTABLECIMIENTO},
        name="restablecer",
    ),
    path("cuenta/", views.MiCuenta.as_view(), name="mi_cuenta"),
]
