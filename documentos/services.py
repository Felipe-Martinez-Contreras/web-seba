"""Operaciones sobre documentos (DOC, ADM-08, ADM-09), cada una con su evento de auditoría."""

import datetime
import logging
import uuid

from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.http import content_disposition_header

from auditoria.services import Accion, registrar
from documentos import almacenamiento, validacion
from documentos.models import Documento, VersionDocumento

logger = logging.getLogger(__name__)


class OperacionNoPermitida(Exception):
    """La operación no corresponde al estado del documento. `motivo` se le muestra a la persona."""

    def __init__(self, motivo):
        super().__init__(motivo)
        self.motivo = motivo


class ArchivoNoDisponible(Exception):
    """El registro existe, pero su archivo no está en el almacenamiento."""


def _detalle(documento, version):
    return f"{documento.titulo[:150]} (versión {version.numero})"


def _guardar_archivo(empresa_id, archivo, validado):
    """Sube el archivo ya validado y devuelve el identificador y la clave de su versión."""
    version_id = uuid.uuid4()
    clave = almacenamiento.clave_de(empresa_id, version_id)
    archivo.seek(0)
    almacenamiento.almacen().guardar(clave, archivo, validado.tipo_mime)
    return version_id, clave


def _crear_version(documento, numero, version_id, clave, validado, actor):
    return VersionDocumento.objects.create(
        id=version_id,
        documento=documento,
        numero=numero,
        clave=clave,
        nombre_original=validado.nombre,
        tipo_mime=validado.tipo_mime,
        extension=validado.extension,
        tamano=validado.tamano,
        sha256=validado.sha256,
        subido_por=actor,
    )


def subir(carpeta, archivo, *, actor, request):
    """Valida el archivo, lo guarda y crea el documento con su primera versión.

    Lanza `ArchivoRechazado` con el motivo. El objeto se guarda antes que las filas; si la
    base falla, se borra: no quedan archivos sin registro.
    """
    validado = validacion.validar(archivo)
    version_id, clave = _guardar_archivo(carpeta.empresa_id, archivo, validado)
    try:
        with transaction.atomic():
            documento = Documento.objects.create(
                empresa_id=carpeta.empresa_id, carpeta=carpeta, titulo=validado.titulo
            )
            version = _crear_version(documento, 1, version_id, clave, validado, actor)
            documento.version_vigente = version
            documento.save(update_fields=["version_vigente", "actualizado_en"])
            registrar(
                Accion.DOCUMENTO_SUBIDO,
                request=request,
                actor=actor,
                empresa=carpeta.empresa,
                objeto=documento,
                detalle=_detalle(documento, version),
            )
    except BaseException:
        almacenamiento.almacen().borrar(clave)
        raise
    return documento


def reemplazar(documento, archivo, *, actor, request):
    """Agrega una versión, que pasa a ser la vigente. Las anteriores se conservan (DOC-08)."""
    validado = validacion.validar(archivo)
    version_id, clave = _guardar_archivo(documento.empresa_id, archivo, validado)
    try:
        with transaction.atomic():
            documento = Documento.objects.select_for_update().get(pk=documento.pk)
            if documento.en_papelera:
                raise OperacionNoPermitida("El documento está en la papelera.")
            ultimo = documento.versiones.aggregate(ultimo=Max("numero"))["ultimo"] or 0
            version = _crear_version(documento, ultimo + 1, version_id, clave, validado, actor)
            documento.version_vigente = version
            documento.save(update_fields=["version_vigente", "actualizado_en"])
            registrar(
                Accion.DOCUMENTO_REEMPLAZADO,
                request=request,
                actor=actor,
                empresa=documento.empresa,
                objeto=documento,
                detalle=_detalle(documento, version),
            )
    except BaseException:
        almacenamiento.almacen().borrar(clave)
        raise
    return version


def editar(documento, *, titulo, descripcion, actor, request):
    anterior = documento.titulo
    with transaction.atomic():
        documento.titulo = titulo
        documento.descripcion = descripcion
        documento.save(update_fields=["titulo", "descripcion", "actualizado_en"])
        registrar(
            Accion.DOCUMENTO_EDITADO,
            request=request,
            actor=actor,
            empresa=documento.empresa,
            objeto=documento,
            detalle=titulo[:150] if titulo == anterior else f"{anterior[:90]} → {titulo[:90]}",
        )
    return documento


def mover(documento, carpeta, *, actor, request):
    """Cambia de carpeta, siempre dentro de la misma empresa (DOC-07)."""
    if carpeta.empresa_id != documento.empresa_id:
        raise OperacionNoPermitida("La carpeta de destino no pertenece a este cliente.")
    origen = documento.carpeta
    if origen.pk == carpeta.pk:
        return False
    with transaction.atomic():
        documento.carpeta = carpeta
        documento.save(update_fields=["carpeta", "actualizado_en"])
        registrar(
            Accion.DOCUMENTO_MOVIDO,
            request=request,
            actor=actor,
            empresa=documento.empresa,
            objeto=documento,
            detalle=f"{documento.titulo[:80]}: {origen.nombre[:50]} → {carpeta.nombre[:50]}",
        )
    return True


def eliminar(documento, *, actor, request):
    """Envía el documento a la papelera. El cliente deja de verlo de inmediato."""
    with transaction.atomic():
        documento.eliminado_en = timezone.now()
        documento.eliminado_por = actor
        documento.save(update_fields=["eliminado_en", "eliminado_por", "actualizado_en"])
        registrar(
            Accion.DOCUMENTO_ELIMINADO,
            request=request,
            actor=actor,
            empresa=documento.empresa,
            objeto=documento,
            detalle=documento.titulo[:150],
        )
    return documento


def limite_de_papelera(ahora=None):
    """Lo eliminado antes de este momento ya no se restaura y se puede purgar."""
    return (ahora or timezone.now()) - datetime.timedelta(days=settings.PAPELERA_DIAS)


def purga_prevista(documento):
    """Desde cuándo `purgar_papelera` puede borrar el documento de forma definitiva."""
    return documento.eliminado_en + datetime.timedelta(days=settings.PAPELERA_DIAS)


def restaurar(documento, *, actor, request):
    """Saca el documento de la papelera, dentro del plazo (ADM-09)."""
    if not documento.en_papelera:
        raise OperacionNoPermitida("El documento no está en la papelera.")
    if documento.eliminado_en < limite_de_papelera():
        raise OperacionNoPermitida(
            f"Pasaron más de {settings.PAPELERA_DIAS} días desde que se eliminó: "
            "ya no se puede restaurar."
        )
    with transaction.atomic():
        documento.eliminado_en = None
        documento.eliminado_por = None
        documento.save(update_fields=["eliminado_en", "eliminado_por", "actualizado_en"])
        registrar(
            Accion.DOCUMENTO_RESTAURADO,
            request=request,
            actor=actor,
            empresa=documento.empresa,
            objeto=documento,
            detalle=documento.titulo[:150],
        )
    return documento


def purgar_vencidos(ahora=None):
    """Borra de forma definitiva, en el almacenamiento y en la base, los documentos que
    superaron el plazo de la papelera. Devuelve cuántos documentos borró.

    Primero los objetos y después las filas: si algo falla a medias, la fila sigue ahí y la
    siguiente ejecución lo reintenta (borrar un objeto que ya no existe no es un error).
    """
    destino = almacenamiento.almacen()
    vencidos = (
        Documento.objects.en_papelera()
        .filter(eliminado_en__lt=limite_de_papelera(ahora))
        .select_related("empresa")
    )
    purgados = 0
    for documento in vencidos:
        versiones = list(documento.versiones.values_list("clave", flat=True))
        for clave in versiones:
            destino.borrar(clave)
        with transaction.atomic():
            registrar(
                Accion.DOCUMENTO_PURGADO,
                empresa=documento.empresa,
                objeto=documento,
                detalle=f"{documento.titulo[:150]} ({len(versiones)} versiones)",
            )
            Documento.objects.filter(pk=documento.pk).update(version_vigente=None)
            documento.versiones.all().purgar()
            documento.delete()
        purgados += 1
    return purgados


def entregar(documento, version, *, ver, actor, request):
    """Registra el evento y devuelve la respuesta que entrega el archivo (DOC-04, DOC-05).

    Quien llama ya comprobó que el usuario puede acceder a este documento y a esta versión.
    `ver` pide abrirlo en el navegador: solo se concede para PDF, JPG y PNG.
    """
    en_linea = ver and version.se_puede_ver
    disposicion = content_disposition_header(not en_linea, version.nombre_original)
    # En una transacción: si el archivo no se puede entregar, no queda un evento que diga
    # que se entregó; y si el evento no se puede registrar, no hay entrega.
    with transaction.atomic():
        registrar(
            Accion.DOCUMENTO_VISTO if en_linea else Accion.DOCUMENTO_DESCARGADO,
            request=request,
            actor=actor,
            empresa=documento.empresa,
            objeto=documento,
            detalle=_detalle(documento, version),
        )
        try:
            return almacenamiento.entregar(
                version.clave, tipo_mime=version.tipo_mime, disposicion=disposicion
            )
        except FileNotFoundError:
            logger.error("Falta en el almacenamiento el archivo de la versión %s", version.pk)
            raise ArchivoNoDisponible from None
