from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Lo que un despliegue necesita antes de reiniciar la aplicación: aplica las "
        "migraciones, crea la tabla de caché y ejecuta check --deploy. Todo en un solo "
        "proceso, para cargar la aplicación una vez y no tres (docs/DESPLIEGUE.md)."
    )

    def handle(self, *args, **opciones):
        salidas = {"stdout": self.stdout, "stderr": self.stderr}
        call_command("migrate", interactive=False, **salidas)
        call_command("createcachetable", **salidas)
        # Si hay un error, termina aquí con código distinto de cero y la aplicación que
        # está en marcha no se toca.
        call_command("check", deploy=True, **salidas)
