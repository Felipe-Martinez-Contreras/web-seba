import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from sitio import contenido


class Command(BaseCommand):
    help = (
        "Escribe en un archivo JSON el contenido del sitio: los datos del negocio, los "
        "servicios y los rubros (sin fotos ni imágenes), sin usuarios, empresas, documentos, "
        "solicitudes ni auditoría. Los datos de prueba de cargar_demo no se exportan. El "
        "archivo trae datos de contacto: no lo guarde en el repositorio. Se carga con "
        "importar_contenido."
    )

    def add_arguments(self, parser):
        parser.add_argument("archivo", help="Ruta del archivo, o - para la salida estándar.")

    def handle(self, *args, **opciones):
        exportacion = contenido.exportar()
        texto = contenido.serializar(exportacion.datos)
        if opciones["archivo"] == "-":
            # Siempre UTF-8 y con saltos de línea de Unix, diga lo que diga la consola.
            if self.stdout._out is sys.stdout and hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", newline="\n")
            self.stdout.write(texto, ending="")
        else:
            try:
                Path(opciones["archivo"]).write_text(texto, encoding="utf-8", newline="\n")
            except OSError as error:
                raise CommandError(f"No se pudo escribir el archivo: {error.strerror}.") from None

        # El resumen va por la salida de errores, para no mezclarse con el archivo, y solo
        # lleva conteos, nombres de campo y slugs.
        servicios = exportacion.datos["servicios"]
        rubros = exportacion.datos["rubros"]
        self._informar(
            f"Exportado: datos del negocio, {len(servicios)} servicios y {len(rubros)} rubros. "
            "Las fotos de los rubros y las imágenes del sitio no viajan: vuelva a subirlas."
        )
        if exportacion.campos_vaciados:
            self._informar(
                "Datos de prueba que se exportaron vacíos: "
                + ", ".join(exportacion.campos_vaciados)
                + "."
            )
        if exportacion.servicios_omitidos:
            self._informar(f"Servicios de prueba omitidos: {exportacion.servicios_omitidos}.")
        if exportacion.rubros_omitidos:
            self._informar(f"Rubros de prueba omitidos: {exportacion.rubros_omitidos}.")
        for anterior, nuevo in exportacion.slugs_cambiados:
            self._informar(f"Identificador de demostración reemplazado: {anterior} -> {nuevo}.")

    def _informar(self, mensaje):
        self.stderr.write(mensaje, style_func=str)
