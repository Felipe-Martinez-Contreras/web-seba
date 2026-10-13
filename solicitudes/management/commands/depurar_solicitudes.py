import logging

from django.core.management.base import BaseCommand, CommandError

from solicitudes import services

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Borra las consultas y cotizaciones recibidas hace más días que "
        "SOLICITUDES_RETENCION_DIAS: es el plazo de conservación que informa la política de "
        "privacidad (SEG-12). Pensado para el cron diario del hosting."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--simular",
            action="store_true",
            help="Dice cuántas se borrarían, sin borrar nada ni dejar un evento de auditoría.",
        )

    def handle(self, *args, **opciones):
        try:
            resultado = services.depurar_vencidas(simular=opciones["simular"])
        except services.PlazoInvalido as error:
            raise CommandError(f"{error} No se borró nada.") from error
        detalle = (
            f"{resultado.total} solicitudes anteriores al {resultado.fecha} "
            f"({resultado.consultas} consultas, {resultado.cotizaciones} cotizaciones)"
        )
        if opciones["simular"]:
            self.stdout.write(f"Simulación: se borrarían {detalle}. No se borró nada.")
            return
        logger.info("Solicitudes depuradas: %s", detalle)
        self.stdout.write(self.style.SUCCESS(f"Se borraron {detalle}."))
