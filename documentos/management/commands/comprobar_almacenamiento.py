import io
import time
import urllib.error
import urllib.request
import uuid

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.http import content_disposition_header

from documentos import almacenamiento

_CONTENIDO = b"%PDF-1.4\n% archivo de prueba de comprobar_almacenamiento\n%%EOF\n"
_TIPO = "application/pdf"


def _estado(url):
    """Código HTTP de un GET, y sus encabezados y cuerpo si respondió 200."""
    try:
        with urllib.request.urlopen(url, timeout=15) as respuesta:
            return respuesta.status, respuesta.headers, respuesta.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, b""


class Command(BaseCommand):
    help = (
        "Comprueba el almacenamiento configurado con un archivo de prueba: lo guarda, lo "
        "lee, pide una URL firmada, verifica que sin firma no se pueda leer y lo borra. "
        "Úselo contra el bucket real, con --firma, antes de cargar documentos (DOC-03, "
        "DOC-04)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--crear-bucket",
            action="store_true",
            help="Crea antes el bucket. Solo para el emulador de S3 de desarrollo.",
        )
        parser.add_argument(
            "--firma",
            action="store_true",
            help=(
                "Comprueba además que una firma alterada se rechace y, tras esperar a que "
                "venza, que la URL deje de servir. Tarda unos 2 minutos. Solo tiene sentido "
                "contra un bucket real: el emulador no valida firmas ni vencimientos."
            ),
        )

    def handle(self, *args, **opciones):
        destino = almacenamiento.almacen()
        if opciones["crear_bucket"]:
            if settings.DOCUMENTOS_ALMACENAMIENTO != "s3":
                raise CommandError("--crear-bucket solo aplica con DOCUMENTOS_ALMACENAMIENTO=s3.")
            destino.crear_bucket()
        clave = almacenamiento.clave_de(uuid.uuid4(), uuid.uuid4())
        self.stdout.write(f"Almacenamiento: {settings.DOCUMENTOS_ALMACENAMIENTO}")
        try:
            destino.guardar(clave, io.BytesIO(_CONTENIDO), _TIPO)
            self._paso("Guardar", destino.existe(clave))
            with destino.abrir(clave) as archivo:
                leido = archivo.read()
            self._paso("Leer el mismo contenido", leido == _CONTENIDO)
            self._paso("Listar", clave in destino.claves())
            disposicion = content_disposition_header(True, "comprobación.pdf")
            url = destino.url_firmada(
                clave,
                tipo_mime=_TIPO,
                disposicion=disposicion,
                segundos=almacenamiento.segundos_de_url(),
            )
            if url is None:
                self.stdout.write(
                    "  URL firmada: no aplica; el almacenamiento local transmite el archivo "
                    "desde la aplicación."
                )
            else:
                self._comprobar_url(url, disposicion)
                if opciones["firma"]:
                    self._comprobar_firma(url)
        finally:
            destino.borrar(clave)
        self._paso("Borrar", not destino.existe(clave))
        self.stdout.write(self.style.SUCCESS("El almacenamiento funciona."))

    def _comprobar_url(self, url, disposicion):
        estado, encabezados, cuerpo = _estado(url)
        self._paso("Descargar con la URL firmada", estado == 200 and cuerpo == _CONTENIDO)
        self._paso(
            "Tipo y disposición en la respuesta",
            encabezados.get("Content-Type", "").startswith(_TIPO)
            and encabezados.get("Content-Disposition") == disposicion,
        )
        self._paso(
            "La URL vence en 120 segundos o menos",
            f"X-Amz-Expires={almacenamiento.segundos_de_url()}" in url,
        )
        sin_firma = url.split("?", 1)[0]
        estado, _, _ = _estado(sin_firma)
        # Un bucket privado responde 403; uno público respondería 200. Va al final: un
        # emulador sin control de acceso falla solo en este paso.
        self._paso(f"Sin firma no se puede leer (respondió {estado})", estado in (401, 403))

    def _comprobar_firma(self, url):
        base, _, firma = url.rpartition("X-Amz-Signature=")
        alterada = base + "X-Amz-Signature=" + ("0" if firma[0] != "0" else "1") + firma[1:]
        estado, _, _ = _estado(alterada)
        self._paso(f"Con la firma alterada no se puede leer (respondió {estado})", estado == 403)
        espera = almacenamiento.segundos_de_url() + 10
        self.stdout.write(f"  Esperando {espera} segundos a que venza la URL...")
        time.sleep(espera)
        estado, _, _ = _estado(url)
        self._paso(f"Vencida, la URL ya no sirve (respondió {estado})", estado == 403)

    def _paso(self, nombre, correcto):
        if not correcto:
            raise CommandError(f"Falló: {nombre}.")
        self.stdout.write(f"  {nombre}: correcto")
