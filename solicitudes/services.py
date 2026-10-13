"""Recepción, notificación y seguimiento de solicitudes (SOL-05 a SOL-11).

El orden es siempre el mismo: primero se guarda la solicitud y después se intenta notificar.
Un fallo del correo nunca la pierde ni llega al visitante.
"""

import datetime
import logging
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from auditoria.services import Accion, registrar
from core import correo, tareas
from solicitudes.models import RETENCION_MINIMA_DIAS, Solicitud

logger = logging.getLogger(__name__)

Notificacion = Solicitud.Notificacion


# --- Recepción ------------------------------------------------------------------------


def recibir(tipo, datos):
    """Guarda la solicitud y deja su notificación en marcha. Devuelve la solicitud.

    La notificación parte cuando la solicitud ya está confirmada en la base y fuera de la
    petición: el visitante no espera al servidor de correo ni se entera de su resultado.
    """
    solicitud = crear_solicitud(tipo, datos)
    tareas.en_segundo_plano(notificar, solicitud.pk)
    return solicitud


def crear_solicitud(tipo, datos):
    """Guarda los datos ya validados por el formulario. No recibe ni guarda la IP."""
    with transaction.atomic():
        return Solicitud.objects.create(
            tipo=tipo,
            nombre=datos["nombre"],
            email=datos["email"],
            telefono=datos.get("telefono", ""),
            empresa=datos.get("empresa", ""),
            servicio=datos.get("servicio"),
            trabajadores=datos.get("trabajadores", ""),
            comuna=datos.get("comuna", ""),
            mensaje=datos["mensaje"],
            consentimiento=datos["consentimiento"],
            consentimiento_en=timezone.now(),
        )


# --- Notificación al profesional ------------------------------------------------------


def url_del_detalle(solicitud):
    """URL absoluta, armada con SITIO_URL y nunca con el encabezado Host de la petición."""
    return settings.SITIO_URL.rstrip("/") + reverse("panel:solicitud", args=[solicitud.pk])


def _enviar(solicitud):
    destinatarios = settings.NOTIFICACIONES_DESTINATARIOS
    if not destinatarios:
        return correo.Resultado.NO_CONFIGURADA, ""
    cuerpo = render_to_string(
        "solicitudes/correo/notificacion.txt",
        {"solicitud": solicitud, "url": url_del_detalle(solicitud)},
    )
    asunto = f"{solicitud.get_tipo_display()} de {solicitud.nombre}"
    # Responder el correo le escribe al visitante (SOL-08). Sin adjuntos y sin copia a él:
    # el formulario no sirve para enviar correos a terceros (SOL-07).
    return correo.enviar(asunto, cuerpo, destinatarios, reply_to=[solicitud.email])


def notificar(solicitud_id):
    """Intenta notificar y registra el resultado en la solicitud. Devuelve el resultado, o
    None si no había nada que hacer.

    La fila queda bloqueada durante el envío: si el hilo de la petición y el cron coinciden,
    el segundo la salta y el profesional no recibe dos correos.
    """
    with transaction.atomic():
        solicitud = (
            Solicitud.objects.select_for_update(skip_locked=True, of=("self",))
            .select_related("servicio")
            .filter(pk=solicitud_id)
            .exclude(notificacion=Notificacion.ENVIADA)
            .first()
        )
        if solicitud is None:
            return None
        resultado, error = _enviar(solicitud)
        solicitud.notificacion = resultado
        solicitud.notificacion_error = error[:200]
        if resultado == correo.Resultado.ENVIADA:
            solicitud.notificada_en = timezone.now()
        if resultado != correo.Resultado.NO_CONFIGURADA:
            solicitud.notificacion_intentos += 1
        solicitud.save(
            update_fields=[
                "notificacion",
                "notificacion_error",
                "notificacion_intentos",
                "notificada_en",
                "actualizado_en",
            ]
        )
    if resultado == correo.Resultado.ENVIADA:
        logger.info("Notificación de solicitud enviada")
    else:
        logger.warning("Notificación de solicitud no enviada: %s", resultado.label)
    return resultado


def reintentar(solicitud, *, actor, request):
    """Reintento pedido desde el panel (SOL-10): dentro de la petición, porque el
    administrador debe ver el resultado."""
    resultado = notificar(solicitud.pk)
    if resultado is not None:
        registrar(
            Accion.SOLICITUD_REINTENTO,
            request=request,
            actor=actor,
            objeto=solicitud,
            detalle=resultado.label,
        )
    return resultado


def reintentar_pendientes():
    """Lo que hace `reintentar_notificaciones` (SOL-11). Devuelve un conteo por resultado."""
    pendientes = Solicitud.objects.por_reintentar(
        maximo_intentos=settings.NOTIFICACIONES_INTENTOS_MAXIMOS,
        ahora=timezone.now(),
        correo_configurado=correo.correo_configurado()
        and bool(settings.NOTIFICACIONES_DESTINATARIOS),
    )
    conteo = {}
    for solicitud_id in list(pendientes.order_by("creado_en").values_list("pk", flat=True)):
        resultado = notificar(solicitud_id)
        if resultado is not None:
            conteo[resultado] = conteo.get(resultado, 0) + 1
    return conteo


# --- Seguimiento en el panel ----------------------------------------------------------


def cambiar_estado(solicitud, estado, *, actor, request):
    """Cambia el estado de seguimiento y lo deja en la auditoría. Devuelve si hubo cambio."""
    if solicitud.estado == estado:
        return False
    tipo, anterior = solicitud.get_tipo_display(), solicitud.get_estado_display()
    with transaction.atomic():
        solicitud.estado = estado
        solicitud.save(update_fields=["estado", "actualizado_en"])
        registrar(
            Accion.SOLICITUD_ESTADO,
            request=request,
            actor=actor,
            objeto=solicitud,
            detalle=f"{tipo}: {anterior} → {solicitud.get_estado_display()}",
        )
    return True


def guardar_notas(solicitud, notas):
    solicitud.notas_internas = notas
    solicitud.save(update_fields=["notas_internas", "actualizado_en"])


# --- Plazo de conservación ------------------------------------------------------------


class PlazoInvalido(Exception):
    """SOLICITUDES_RETENCION_DIAS está bajo el mínimo: no se borra nada."""


def plazo_de_retencion():
    """Los días que se conserva una solicitud. Falla si la configuración está bajo el mínimo."""
    dias = settings.SOLICITUDES_RETENCION_DIAS
    if dias < RETENCION_MINIMA_DIAS:
        raise PlazoInvalido(
            f"SOLICITUDES_RETENCION_DIAS vale {dias} y el mínimo es {RETENCION_MINIMA_DIAS}: "
            "con menos se borrarían solicitudes que todavía se están atendiendo."
        )
    return dias


@dataclass(frozen=True)
class Depuracion:
    limite: datetime.datetime
    consultas: int
    cotizaciones: int

    @property
    def total(self):
        return self.consultas + self.cotizaciones

    @property
    def fecha(self):
        return date_format(timezone.localtime(self.limite), "d-m-Y")


def depurar_vencidas(*, simular=False):
    """Lo que hace `depurar_solicitudes`: borra las consultas y cotizaciones que superaron
    el plazo de conservación. Con `simular` solo cuenta.

    Con la fila se van sus notas internas y el estado de su notificación. El evento de
    auditoría lleva el conteo y la fecha de corte, nunca datos de las personas.
    """
    dias, ahora = plazo_de_retencion(), timezone.now()
    limite = ahora - datetime.timedelta(days=dias)
    with transaction.atomic():
        vencidas = Solicitud.objects.vencidas(ahora=ahora, dias=dias)
        por_tipo = dict(vencidas.values_list("tipo").annotate(Count("pk")))
        resultado = Depuracion(
            limite=limite,
            consultas=por_tipo.get(Solicitud.Tipo.CONSULTA, 0),
            cotizaciones=por_tipo.get(Solicitud.Tipo.COTIZACION, 0),
        )
        if resultado.total and not simular:
            vencidas.delete()
            # La depuración deja su propio rastro, igual que la de la auditoría.
            registrar(
                Accion.SOLICITUDES_DEPURADAS,
                detalle=(
                    f"{resultado.total} solicitudes anteriores al {resultado.fecha} "
                    f"({resultado.consultas} consultas, {resultado.cotizaciones} cotizaciones)"
                ),
            )
    return resultado
