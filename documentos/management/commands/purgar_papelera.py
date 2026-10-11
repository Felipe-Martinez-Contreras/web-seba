import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from documentos import services

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Borra de forma definitiva, en la base de datos y en el almacenamiento, los "
        "documentos que llevan en la papelera más días que PAPELERA_DIAS (ADM-09). "
        "Pensado para el cron diario del hosting."
    )

    def handle(self, *args, **opciones):
        purgados = services.purgar_vencidos()
        logger.info("Papelera purgada: %s documentos", purgados)
        self.stdout.write(
            self.style.SUCCESS(
                f"Se borraron definitivamente {purgados} documentos con más de "
                f"{settings.PAPELERA_DIAS} días en la papelera."
            )
        )
