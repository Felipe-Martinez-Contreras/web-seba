"""Registro de eventos de auditoría (AUD-01, AUD-02)."""

import uuid

from auditoria.models import EventoAuditoria
from core import rut as utilidades_rut

Accion = EventoAuditoria.Accion


def _uuid_de(objeto):
    valor = getattr(objeto, "uuid", None) or objeto.pk
    return valor if isinstance(valor, uuid.UUID) else None


def registrar(
    accion,
    *,
    request=None,
    actor=None,
    rut_intentado="",
    empresa=None,
    objeto=None,
    detalle="",
    ip=None,
):
    """Agrega un evento. Nunca recibe contraseñas, tokens ni enlaces: el detalle es un texto fijo.

    La IP sale de `request.ip_cliente` (core.ip), no de un encabezado cualquiera.
    """
    if request is not None and ip is None:
        ip = getattr(request, "ip_cliente", None)
    if empresa is None and actor is not None:
        empresa = actor.empresa
    return EventoAuditoria.objects.create(
        accion=accion,
        actor=actor,
        rut_intentado=(
            utilidades_rut.normalizar(rut_intentado)
            if utilidades_rut.es_valido(rut_intentado)
            else ""
        ),
        empresa=empresa,
        objeto_tipo=objeto._meta.model_name if objeto is not None else "",
        objeto_uuid=_uuid_de(objeto) if objeto is not None else None,
        ip=ip,
        detalle=detalle[:200],
    )
