"""Estado de una cuenta tal como lo ve el administrador (ADM-06).

Único lugar donde se decide: inactivo, bloqueado, pendiente o activo, en ese orden de
precedencia. El estado siempre lleva texto; el tono solo lo acompaña.
"""

from dataclasses import dataclass

from django.utils import timezone
from django.utils.formats import date_format

from cuentas import bloqueo
from cuentas.models import EnlaceAcceso


@dataclass(frozen=True)
class Estado:
    clave: str
    texto: str
    tono: str
    detalle: str = ""


INACTIVO = "inactivo"
BLOQUEADO = "bloqueado"
PENDIENTE = "pendiente"
ACTIVO = "activo"


def _detalle_del_enlace(expira_en, ahora):
    if expira_en is None:
        return "Sin enlace de activación vigente"
    if expira_en <= ahora:
        return "Enlace de activación vencido"
    vence = date_format(timezone.localtime(expira_en), "d-m-Y H:i")
    return f"Enlace vigente hasta el {vence}"


def anotar_estados(usuarios):
    """Agrega `estado` a cada usuario de la lista, sin consultas por fila."""
    usuarios = list(usuarios)
    bloqueados = bloqueo.ruts_bloqueados(usuario.rut for usuario in usuarios)
    pendientes = {usuario.pk for usuario in usuarios if not usuario.has_usable_password()}
    # Generar un enlace revoca los anteriores: queda a lo más uno sin usar por cuenta.
    vencimientos = dict(
        EnlaceAcceso.objects.filter(
            usuario__in=pendientes, usado_en__isnull=True, revocado_en__isnull=True
        ).values_list("usuario_id", "expira_en")
    )
    ahora = timezone.now()
    for usuario in usuarios:
        if not usuario.is_active:
            usuario.estado = Estado(INACTIVO, "Inactivo", "neutro")
        elif usuario.rut in bloqueados:
            usuario.estado = Estado(BLOQUEADO, "Bloqueado", "error", "Por intentos fallidos")
        elif usuario.pk in pendientes:
            usuario.estado = Estado(
                PENDIENTE,
                "Pendiente",
                "advertencia",
                _detalle_del_enlace(vencimientos.get(usuario.pk), ahora),
            )
        else:
            usuario.estado = Estado(ACTIVO, "Activo", "exito")
    return usuarios
