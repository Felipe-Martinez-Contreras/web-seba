"""Tope del tamaño de una petición con archivos, aplicado antes de leer su cuerpo (SEG-07)."""

from django.core.exceptions import RequestDataTooBig
from django.core.files.uploadhandler import FileUploadHandler

from documentos import validacion

# La subida con JavaScript envía un archivo por petición. Sin JavaScript van todos juntos:
# hasta este número de archivos del tamaño máximo caben en una sola petición.
ARCHIVOS_POR_PETICION = 4
_MARGEN = 1024 * 1024


def peticion_maxima():
    return validacion.tamano_maximo() * ARCHIVOS_POR_PETICION + _MARGEN


class LimiteDePeticion(FileUploadHandler):
    """Primer manejador de subidas: si la petición declara más bytes que el tope, se
    rechaza con un 400 sin recibir el archivo. El tamaño de cada archivo, con su motivo,
    lo comprueba después `validacion.validar`."""

    def handle_raw_input(self, input_data, META, content_length, boundary, encoding=None):
        if content_length > peticion_maxima():
            raise RequestDataTooBig("La petición supera el tamaño máximo de subida.")

    def receive_data_chunk(self, raw_data, start):
        return raw_data

    def file_complete(self, file_size):
        return None
