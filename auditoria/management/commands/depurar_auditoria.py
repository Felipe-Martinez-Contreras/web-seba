import calendar
import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.formats import date_format

from auditoria.models import EventoAuditoria
from auditoria.services import Accion, registrar

logger = logging.getLogger(__name__)


def restar_meses(fecha, meses):
    """La misma fecha, `meses` meses antes; si ese día no existe, el último del mes."""
    total = fecha.year * 12 + fecha.month - 1 - meses
    anio, mes = divmod(total, 12)
    dia = min(fecha.day, calendar.monthrange(anio, mes + 1)[1])
    return fecha.replace(year=anio, month=mes + 1, day=dia)


class Command(BaseCommand):
    help = (
        "Borra los eventos de auditoría más antiguos que la retención configurada en "
        "AUDITORIA_RETENCION_MESES (AUD-03). Pensado para el cron mensual del hosting."
    )

    def handle(self, *args, **opciones):
        meses = settings.AUDITORIA_RETENCION_MESES
        if meses < 1:
            raise CommandError("AUDITORIA_RETENCION_MESES debe ser 1 o más.")
        limite = restar_meses(timezone.now(), meses)
        borrados = EventoAuditoria.objects.depurar(limite)
        fecha = date_format(timezone.localtime(limite), "d-m-Y")
        if borrados:
            # La depuración deja su propio rastro: la auditoría no se acorta en silencio.
            registrar(
                Accion.AUDITORIA_DEPURADA, detalle=f"{borrados} eventos anteriores al {fecha}"
            )
        logger.info("Auditoría depurada: %s eventos anteriores al %s", borrados, fecha)
        self.stdout.write(
            self.style.SUCCESS(f"Se borraron {borrados} eventos anteriores al {fecha}.")
        )
