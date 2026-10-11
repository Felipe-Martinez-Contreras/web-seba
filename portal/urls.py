from django.urls import path

from portal import views

app_name = "portal"

urlpatterns = [
    path("", views.Inicio.as_view(), name="inicio"),
    path("carpetas/", views.Carpetas.as_view(), name="carpetas"),
    path("carpetas/<uuid:carpeta>/", views.CarpetaDetalle.as_view(), name="carpeta"),
    path("buscar/", views.Buscar.as_view(), name="buscar"),
    path("documentos/<uuid:documento>/", views.DocumentoDetalle.as_view(), name="documento"),
    path("documentos/<uuid:documento>/ver/", views.DocumentoVer.as_view(), name="documento_ver"),
    path(
        "documentos/<uuid:documento>/descargar/",
        views.DocumentoDescargar.as_view(),
        name="documento_descargar",
    ),
]
