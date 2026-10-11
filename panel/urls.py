from django.urls import include, path

from panel import views

app_name = "panel"

# Todo lo de un cliente cuelga de su UUID: usuarios, carpetas y documentos se buscan dentro
# de él.
_de_cliente = [
    path("", views.Cliente.as_view(), name="cliente"),
    path("documentos/", views.ClienteDocumentos.as_view(), name="cliente_documentos"),
    path("usuarios/", views.ClienteUsuarios.as_view(), name="cliente_usuarios"),
    path("actividad/", views.ClienteActividad.as_view(), name="cliente_actividad"),
    path("editar/", views.ClienteEditar.as_view(), name="cliente_editar"),
    path("estado/", views.ClienteEstado.as_view(), name="cliente_estado"),
    path("carpetas/nueva/", views.CarpetaNueva.as_view(), name="carpeta_nueva"),
    path("carpetas/<uuid:carpeta>/", views.CarpetaDetalle.as_view(), name="carpeta"),
    path("carpetas/<uuid:carpeta>/subir/", views.DocumentoSubir.as_view(), name="documento_subir"),
    path("carpetas/<uuid:carpeta>/editar/", views.CarpetaEditar.as_view(), name="carpeta_editar"),
    path("carpetas/<uuid:carpeta>/mover/", views.CarpetaMover.as_view(), name="carpeta_mover"),
    path(
        "carpetas/<uuid:carpeta>/eliminar/",
        views.CarpetaEliminar.as_view(),
        name="carpeta_eliminar",
    ),
    path("papelera/", views.ClientePapelera.as_view(), name="cliente_papelera"),
    path("documentos/<uuid:documento>/", views.DocumentoDetalle.as_view(), name="documento"),
    path(
        "documentos/<uuid:documento>/editar/",
        views.DocumentoEditar.as_view(),
        name="documento_editar",
    ),
    path(
        "documentos/<uuid:documento>/mover/",
        views.DocumentoMover.as_view(),
        name="documento_mover",
    ),
    path(
        "documentos/<uuid:documento>/reemplazar/",
        views.DocumentoReemplazar.as_view(),
        name="documento_reemplazar",
    ),
    path(
        "documentos/<uuid:documento>/eliminar/",
        views.DocumentoEliminar.as_view(),
        name="documento_eliminar",
    ),
    path(
        "documentos/<uuid:documento>/restaurar/",
        views.DocumentoRestaurar.as_view(),
        name="documento_restaurar",
    ),
    path(
        "documentos/<uuid:documento>/versiones/<uuid:version>/ver/",
        views.VersionVer.as_view(),
        name="version_ver",
    ),
    path(
        "documentos/<uuid:documento>/versiones/<uuid:version>/descargar/",
        views.VersionDescargar.as_view(),
        name="version_descargar",
    ),
    path("usuarios/nuevo/", views.UsuarioNuevo.as_view(), name="usuario_nuevo"),
    path("usuarios/<uuid:usuario>/editar/", views.UsuarioEditar.as_view(), name="usuario_editar"),
    path("usuarios/<uuid:usuario>/estado/", views.UsuarioEstado.as_view(), name="usuario_estado"),
    path("usuarios/<uuid:usuario>/enlace/", views.UsuarioEnlace.as_view(), name="usuario_enlace"),
    path(
        "usuarios/<uuid:usuario>/desbloquear/",
        views.UsuarioDesbloquear.as_view(),
        name="usuario_desbloquear",
    ),
]

urlpatterns = [
    path("", views.Inicio.as_view(), name="inicio"),
    path("clientes/", views.Clientes.as_view(), name="clientes"),
    path("clientes/nuevo/", views.ClienteNuevo.as_view(), name="cliente_nuevo"),
    path("clientes/<uuid:empresa>/", include(_de_cliente)),
    path("auditoria/", views.Auditoria.as_view(), name="auditoria"),
]
