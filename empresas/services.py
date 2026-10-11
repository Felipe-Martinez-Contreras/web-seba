"""Alta y cambios de empresas y carpetas (ADM-03, ADM-04, ADM-07), con su auditoría."""

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Max, ProtectedError, Q

from auditoria.services import Accion, registrar
from empresas.models import Carpeta


class CarpetaConDocumentos(Exception):
    """La carpeta tiene documentos, vigentes o en la papelera, y no se puede eliminar (ADM-07)."""

    def __init__(self, vigentes, en_papelera):
        super().__init__("La carpeta tiene documentos.")
        self.vigentes = vigentes
        self.en_papelera = en_papelera

    @property
    def motivo(self):
        total = self.vigentes + self.en_papelera
        documentos = "1 documento" if total == 1 else f"{total} documentos"
        return (
            f"No se puede eliminar: la carpeta tiene {documentos} "
            f"({self.en_papelera} en la papelera). Muévalos a otra carpeta o espere a que "
            "la papelera se vacíe."
        )


SUBIR = "subir"
BAJAR = "bajar"


def _campos_cambiados(formulario):
    """Nombres de los campos modificados, para el detalle de la auditoría. Nunca sus valores."""
    etiquetas = [str(formulario.fields[campo].label).lower() for campo in formulario.changed_data]
    return ("Cambió: " + ", ".join(etiquetas)) if etiquetas else ""


# --- Empresas -------------------------------------------------------------------------


def crear_empresa(formulario, *, con_carpetas_base, actor, request):
    """Guarda la empresa y, si se pidió, sus carpetas base, en una sola transacción."""
    with transaction.atomic():
        empresa = formulario.save()
        if con_carpetas_base:
            Carpeta.objects.bulk_create(
                Carpeta(empresa=empresa, nombre=nombre, orden=orden)
                for orden, nombre in enumerate(settings.CARPETAS_BASE, start=1)
            )
        registrar(
            Accion.EMPRESA_CREADA,
            request=request,
            actor=actor,
            empresa=empresa,
            objeto=empresa,
            detalle="Con carpetas base" if con_carpetas_base else "Sin carpetas base",
        )
    return empresa


def editar_empresa(formulario, *, actor, request):
    with transaction.atomic():
        empresa = formulario.save()
        registrar(
            Accion.EMPRESA_EDITADA,
            request=request,
            actor=actor,
            empresa=empresa,
            objeto=empresa,
            detalle=_campos_cambiados(formulario),
        )
    return empresa


def cambiar_estado_empresa(empresa, activa, *, actor, request):
    """Desactiva o reactiva. Desactivar corta el acceso de sus usuarios en la petición
    siguiente (AUT-11): lo comprueba el backend de autenticación. Devuelve si hubo cambio."""
    if empresa.activa == activa:
        return False
    with transaction.atomic():
        empresa.activa = activa
        empresa.save(update_fields=["activa", "actualizado_en"])
        registrar(
            Accion.EMPRESA_REACTIVADA if activa else Accion.EMPRESA_DESACTIVADA,
            request=request,
            actor=actor,
            empresa=empresa,
            objeto=empresa,
        )
    return True


# --- Carpetas -------------------------------------------------------------------------


def crear_carpeta(empresa, *, nombre, descripcion, actor, request):
    """Agrega la carpeta al final de la lista de la empresa."""
    with transaction.atomic():
        ultimo = empresa.carpetas.aggregate(ultimo=Max("orden"))["ultimo"] or 0
        carpeta = Carpeta.objects.create(
            empresa=empresa, nombre=nombre, descripcion=descripcion, orden=ultimo + 1
        )
        registrar(
            Accion.CARPETA_CREADA,
            request=request,
            actor=actor,
            empresa=empresa,
            objeto=carpeta,
            detalle=carpeta.nombre,
        )
    return carpeta


def editar_carpeta(carpeta, *, nombre, descripcion, actor, request):
    anterior = carpeta.nombre
    with transaction.atomic():
        carpeta.nombre = nombre
        carpeta.descripcion = descripcion
        carpeta.save(update_fields=["nombre", "descripcion", "actualizado_en"])
        registrar(
            Accion.CARPETA_EDITADA,
            request=request,
            actor=actor,
            empresa=carpeta.empresa,
            objeto=carpeta,
            detalle=nombre if nombre == anterior else f"{anterior} → {nombre}",
        )
    return carpeta


def mover_carpeta(carpeta, direccion):
    """Sube o baja la carpeta un lugar y deja el orden de la empresa numerado desde 1."""
    with transaction.atomic():
        carpetas = list(Carpeta.objects.select_for_update().filter(empresa_id=carpeta.empresa_id))
        posicion = next(i for i, otra in enumerate(carpetas) if otra.pk == carpeta.pk)
        destino = posicion - 1 if direccion == SUBIR else posicion + 1
        if not 0 <= destino < len(carpetas):
            return False
        carpetas[posicion], carpetas[destino] = carpetas[destino], carpetas[posicion]
        for orden, otra in enumerate(carpetas, start=1):
            otra.orden = orden
        Carpeta.objects.bulk_update(carpetas, ["orden"])
    return True


def contar_documentos(carpeta):
    """Documentos de la carpeta: (vigentes, en la papelera)."""
    conteo = carpeta.documentos.aggregate(
        vigentes=Count("pk", filter=Q(eliminado_en__isnull=True)),
        en_papelera=Count("pk", filter=Q(eliminado_en__isnull=False)),
    )
    return conteo["vigentes"], conteo["en_papelera"]


def eliminar_carpeta(carpeta, *, actor, request):
    """Elimina la carpeta solo si no tiene documentos, contando los de la papelera (ADM-07).

    El bloqueo de la fila hace esperar a una subida simultánea a esta carpeta; además la
    base la protege (`PROTECT`): con un documento dentro, la carpeta no se puede borrar.
    """
    with transaction.atomic():
        Carpeta.objects.select_for_update().get(pk=carpeta.pk)
        vigentes, en_papelera = contar_documentos(carpeta)
        if vigentes or en_papelera:
            raise CarpetaConDocumentos(vigentes, en_papelera)
        registrar(
            Accion.CARPETA_ELIMINADA,
            request=request,
            actor=actor,
            empresa=carpeta.empresa,
            objeto=carpeta,
            detalle=carpeta.nombre,
        )
        try:
            carpeta.delete()
        except ProtectedError:
            raise CarpetaConDocumentos(*contar_documentos(carpeta)) from None
