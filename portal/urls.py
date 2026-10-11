from django.urls import path

from portal import views

app_name = "portal"

urlpatterns = [
    path("", views.Inicio.as_view(), name="inicio"),
    path("documentos/<uuid:documento>/ver/", views.DocumentoVer.as_view(), name="documento_ver"),
    path(
        "documentos/<uuid:documento>/descargar/",
        views.DocumentoDescargar.as_view(),
        name="documento_descargar",
    ),
]
