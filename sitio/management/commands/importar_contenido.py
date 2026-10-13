import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from sitio import contenido


class Command(BaseCommand):
    help = (
        "Carga el contenido del sitio desde un archivo de exportar_contenido, en una base que "
        "todavía no lo tiene. Repetirlo con el mismo archivo no cambia nada. Falla, sin "
        "modificar la base, si el archivo trae algo inesperado o si la base ya tiene otro "
        "contenido."
    )

    def add_arguments(self, parser):
        parser.add_argument("archivo", help="Ruta del archivo, o - para la entrada estándar.")

    def handle(self, *args, **opciones):
        try:
            if opciones["archivo"] == "-":
                crudo = sys.stdin.buffer.read()
            else:
                crudo = Path(opciones["archivo"]).read_bytes()
        except OSError as error:
            raise CommandError(f"No se pudo leer el archivo: {error.strerror}.") from None
        try:
            # utf-8-sig: un archivo guardado desde Windows puede empezar con la marca BOM.
            texto = crudo.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise CommandError("El archivo no está en UTF-8.") from None

        try:
            importacion = contenido.importar(contenido.leer(texto))
        except contenido.ErrorDeContenido as error:
            raise CommandError(f"No se importó nada.\n{error}") from None

        if importacion.sin_cambios:
            self.stdout.write("El contenido ya estaba cargado: no se cambió nada.")
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"Importado: {importacion.campos} datos del negocio y "
                f"{importacion.servicios_creados} servicios."
            )
        )
