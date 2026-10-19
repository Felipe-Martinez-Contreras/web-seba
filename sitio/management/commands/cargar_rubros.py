from django.core.management.base import BaseCommand

from sitio import rubros


class Command(BaseCommand):
    help = (
        "Crea los rubros de partida de «Áreas en las que trabajamos», sin fotos (PUB-09). "
        "Solo actúa si todavía no hay ningún rubro: repetirlo no duplica nada ni vuelve a "
        "crear los que se eliminaron en el panel."
    )

    def handle(self, *args, **opciones):
        creados = rubros.cargar_iniciales()
        if not creados:
            self.stdout.write("Ya hay rubros: no se cambió nada. Edítelos en el panel.")
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"Se crearon {creados} rubros, sin fotos. Súbalas en el panel: Configuración › "
                "Contenido del sitio › Rubros."
            )
        )
