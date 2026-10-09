from django.urls import path

from panel import views

app_name = "panel"

urlpatterns = [
    path("", views.Inicio.as_view(), name="inicio"),
    path(
        "usuarios/<uuid:uuid>/desbloquear/",
        views.DesbloquearUsuario.as_view(),
        name="usuario_desbloquear",
    ),
]
