from django.urls import include, path

from panel import views
from solicitudes.models import Solicitud

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

_de_solicitud = [
    path("", views.SolicitudDetalle.as_view(), name="solicitud"),
    path("estado/", views.SolicitudEstado.as_view(), name="solicitud_estado"),
    path("notas/", views.SolicitudNotas.as_view(), name="solicitud_notas"),
    path("reintentar/", views.SolicitudReintentar.as_view(), name="solicitud_reintentar"),
]

_de_servicio = [
    path("editar/", views.ServicioEditar.as_view(), name="servicio_editar"),
    path("mover/", views.ServicioMover.as_view(), name="servicio_mover"),
    path("estado/", views.ServicioEstado.as_view(), name="servicio_estado"),
]

_de_rubro = [
    path("editar/", views.RubroEditar.as_view(), name="rubro_editar"),
    path("foto/quitar/", views.RubroQuitarFoto.as_view(), name="rubro_quitar_foto"),
    path("mover/", views.RubroMover.as_view(), name="rubro_mover"),
    path("estado/", views.RubroEstado.as_view(), name="rubro_estado"),
    path("eliminar/", views.RubroEliminar.as_view(), name="rubro_eliminar"),
]

urlpatterns = [
    path("", views.Inicio.as_view(), name="inicio"),
    path("clientes/", views.Clientes.as_view(), name="clientes"),
    path("clientes/nuevo/", views.ClienteNuevo.as_view(), name="cliente_nuevo"),
    path("clientes/<uuid:empresa>/", include(_de_cliente)),
    path("auditoria/", views.Auditoria.as_view(), name="auditoria"),
    path(
        "solicitudes/consultas/",
        views.Solicitudes.as_view(tipo=Solicitud.Tipo.CONSULTA),
        name="solicitudes_consultas",
    ),
    path(
        "solicitudes/cotizaciones/",
        views.Solicitudes.as_view(tipo=Solicitud.Tipo.COTIZACION),
        name="solicitudes_cotizaciones",
    ),
    path("solicitudes/<uuid:solicitud>/", include(_de_solicitud)),
    path("contenido/", views.Contenido.as_view(), name="contenido"),
    path("contenido/servicios/", views.Servicios.as_view(), name="servicios"),
    path("contenido/servicios/nuevo/", views.ServicioNuevo.as_view(), name="servicio_nuevo"),
    path("contenido/servicios/<int:servicio>/", include(_de_servicio)),
    path("contenido/rubros/", views.Rubros.as_view(), name="rubros"),
    path("contenido/rubros/nuevo/", views.RubroNuevo.as_view(), name="rubro_nuevo"),
    path("contenido/rubros/<int:rubro>/", include(_de_rubro)),
    path("contenido/imagenes/", views.Imagenes.as_view(), name="imagenes"),
    path("contenido/imagenes/<slug:ranura>/", views.ImagenCambiar.as_view(), name="imagen_cambiar"),
    path(
        "contenido/imagenes/<slug:ranura>/restaurar/",
        views.ImagenRestaurar.as_view(),
        name="imagen_restaurar",
    ),
]
