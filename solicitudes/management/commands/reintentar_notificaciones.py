import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from core import correo
from solicitudes import services

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Vuelve a intentar las notificaciones de solicitudes que fallaron, hasta "
        "NOTIFICACIONES_INTENTOS_MAXIMOS, y envía las que quedaron sin intentar (SOL-11). "
        "Pensado para el cron del hosting, cada 15 minutos."
    )

    def handle(self, *args, **opciones):
        conteo = services.reintentar_pendientes()
        if not conteo:
            self.stdout.write("No hay notificaciones por reintentar.")
            return
        enviadas = conteo.get(correo.Resultado.ENVIADA, 0)
        fallidas = conteo.get(correo.Resultado.FALLIDA, 0)
        sin_configurar = conteo.get(correo.Resultado.NO_CONFIGURADA, 0)
        logger.info(
            "Notificaciones reintentadas: %s enviadas, %s fallidas, %s sin configuración",
            enviadas,
            fallidas,
            sin_configurar,
        )
        self.stdout.write(
            f"Enviadas: {enviadas}. Fallidas: {fallidas}. Sin configuración de correo: "
            f"{sin_configurar}. Máximo de intentos por solicitud: "
            f"{settings.NOTIFICACIONES_INTENTOS_MAXIMOS}."
        )
