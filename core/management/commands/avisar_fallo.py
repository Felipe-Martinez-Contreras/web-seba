import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core import avisos, correo

_NOMBRE = re.compile(r"[\w@.:-]{1,80}")


class Command(BaseCommand):
    help = (
        "Avisa por correo a ERRORES_DESTINATARIOS que una tarea programada falló. Lo llama "
        "systemd cuando una tarea o el respaldo terminan con error (docs/DESPLIEGUE.md)."
    )

    def add_arguments(self, parser):
        parser.add_argument("tarea", help="Nombre de la tarea o de la unidad que falló.")

    def handle(self, *args, **opciones):
        tarea = opciones["tarea"]
        if not _NOMBRE.fullmatch(tarea):
            raise CommandError("El nombre de la tarea solo admite letras, números y . : @ - _")
        destinatarios = settings.ERRORES_DESTINATARIOS
        if not destinatarios:
            raise CommandError("No se avisó: falta ERRORES_DESTINATARIOS.")
        sitio = avisos.nombre_del_sitio()
        cuerpo = "\n".join(
            [
                f"Sitio: {sitio}",
                f"Fecha: {timezone.localtime().strftime('%d-%m-%Y %H:%M:%S')}",
                f"Tarea: {tarea}",
                "",
                "La tarea terminó con error. Para ver el motivo, en el servidor:",
                f"  journalctl -u 'webseba-*{tarea}*' --since '-1 day'",
            ]
        )
        resultado, error = correo.enviar(
            f"[{sitio}] Falló la tarea programada {tarea}", cuerpo, destinatarios
        )
        if resultado == correo.Resultado.NO_CONFIGURADA:
            raise CommandError("No se avisó: correo no configurado.")
        if resultado != correo.Resultado.ENVIADA:
            raise CommandError(f"No se avisó: el envío falló ({error}).")
        self.stdout.write(self.style.SUCCESS("Aviso enviado."))
