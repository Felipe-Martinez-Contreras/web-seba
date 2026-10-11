from itertools import groupby

from django.core.management.base import BaseCommand, CommandError

from sitio import services


class Command(BaseCommand):
    help = (
        "Lista el contenido que falta completar antes de publicar el sitio: los datos "
        "[COMPLETAR], los datos de prueba y la configuración del correo (PUB-06). "
        "Con --estricto termina con error si queda algo pendiente."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--estricto",
            action="store_true",
            help="Termina con código 1 si hay algo pendiente. Útil antes de publicar.",
        )

    def handle(self, *args, **opciones):
        pendientes = services.contenido_pendiente()
        if not pendientes:
            self.stdout.write(self.style.SUCCESS("No hay contenido pendiente."))
            return

        self.stdout.write(f"Contenido pendiente [COMPLETAR]: {len(pendientes)}")
        for grupo, elementos in groupby(pendientes, key=lambda pendiente: pendiente.grupo):
            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING(grupo))
            for pendiente in elementos:
                marca = " (bloquea los formularios)" if pendiente.bloqueante else ""
                self.stdout.write(f"  - {pendiente.nombre}: {pendiente.detalle}{marca}")
                self.stdout.write(f"    Dónde: {pendiente.donde}")
        self.stdout.write("")
        self.stdout.write("Lo que falta no se muestra en el sitio público.")
        if opciones["estricto"]:
            raise CommandError(f"Quedan {len(pendientes)} pendientes.")
