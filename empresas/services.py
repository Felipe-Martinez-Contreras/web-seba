"""Alta y cambios de empresas y carpetas (ADM-03, ADM-04, ADM-07), con su auditoría."""

from django.conf import settings
from django.db import transaction
from django.db.models import Max

from auditoria.services import Accion, registrar
from empresas.models import Carpeta

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


def eliminar_carpeta(carpeta, *, actor, request):
    with transaction.atomic():
        registrar(
            Accion.CARPETA_ELIMINADA,
            request=request,
            actor=actor,
            empresa=carpeta.empresa,
            objeto=carpeta,
            detalle=carpeta.nombre,
        )
        carpeta.delete()
