"""Almacenamiento privado de los archivos (DOC-03, DOC-04).

Dos implementaciones con las mismas operaciones: `AlmacenLocal` (una carpeta fuera de toda
ruta pública) y `AlmacenS3` (un bucket privado compatible con S3). El resto de la aplicación
solo usa `almacen()` y `entregar()`, así que el código de subida y de descarga es el mismo
en desarrollo y en producción.
"""

import functools
import os
import re
import tempfile
import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import FileResponse, HttpResponseRedirect

_UUID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
# Única forma válida de una clave: la exigen esta capa y una restricción de la base.
PATRON_CLAVE = rf"^docs/{_UUID}/{_UUID}$"
_CLAVE = re.compile(PATRON_CLAVE)

# Tope de la vigencia de una URL firmada, diga lo que diga la configuración (DOC-04).
MAXIMO_URL_SEGUNDOS = 120
_TROZO = 64 * 1024


class ClaveInvalida(ValueError):
    """La clave no tiene la forma `docs/<uuid_empresa>/<uuid_version>`."""


def clave_de(empresa_id, version_id):
    """Clave de almacenamiento de una versión: dos UUID aleatorios y nada más. Sin nombre
    de archivo, sin extensión y sin RUT (DOC-03)."""
    return f"docs/{uuid.UUID(str(empresa_id))}/{uuid.UUID(str(version_id))}"


def _comprobar(clave):
    if not _CLAVE.fullmatch(clave):
        raise ClaveInvalida("Clave de almacenamiento con una forma no admitida.")
    return clave


class AlmacenLocal:
    """Archivos en una carpeta del servidor. Ninguna URL la sirve: solo `entregar()` lee de ella."""

    def __init__(self, raiz):
        self.raiz = Path(raiz)

    def _ruta(self, clave):
        return self.raiz / _comprobar(clave)

    def guardar(self, clave, archivo, tipo_mime):
        """Escribe por trozos en un temporal y lo renombra: nunca queda un archivo a medias."""
        ruta = self._ruta(clave)
        if ruta.exists():
            raise FileExistsError("Ya existe un objeto con esa clave.")
        ruta.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporal = tempfile.mkstemp(dir=ruta.parent, prefix=".subiendo-")
        try:
            with os.fdopen(descriptor, "wb") as destino:
                while trozo := archivo.read(_TROZO):
                    destino.write(trozo)
            os.replace(temporal, ruta)
        except BaseException:
            Path(temporal).unlink(missing_ok=True)
            raise

    def abrir(self, clave):
        return self._ruta(clave).open("rb")

    def existe(self, clave):
        return self._ruta(clave).is_file()

    def borrar(self, clave):
        """Borra el objeto. Que ya no exista no es un error: la purga se puede reintentar."""
        self._ruta(clave).unlink(missing_ok=True)

    def claves(self):
        base = self.raiz / "docs"
        if not base.is_dir():
            return []
        return sorted(
            ruta.relative_to(self.raiz).as_posix() for ruta in base.rglob("*") if ruta.is_file()
        )

    def url_firmada(self, clave, *, tipo_mime, disposicion, segundos):
        """No hay URL: el archivo se transmite desde la propia aplicación."""
        return None


class AlmacenS3:
    """Bucket privado compatible con S3. `boto3` se importa solo aquí: con el almacenamiento
    local no se carga en memoria."""

    def __init__(self, *, bucket, endpoint_url, region, access_key_id, secret_access_key):
        import boto3
        from botocore.config import Config

        self.bucket = bucket
        self._cliente = boto3.client(
            "s3",
            endpoint_url=endpoint_url or None,
            region_name=region or None,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=Config(
                signature_version="s3v4",
                # Con un endpoint propio (otro proveedor o un emulador) el bucket va en la ruta.
                s3={"addressing_style": "path" if endpoint_url else "auto"},
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=5,
                read_timeout=30,
                # Desde boto3 1.36 cada subida lleva una suma de verificación que Google
                # Cloud Storage rechaza ("SignatureDoesNotMatch"). Solo cuando la operación
                # la exija, que es lo que entienden los servicios compatibles con S3.
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
            ),
        )

    def crear_bucket(self):
        """Solo para el emulador de desarrollo: en producción el bucket ya existe y las
        credenciales, de permisos mínimos, no pueden crear uno (SEG-08)."""
        from botocore.exceptions import ClientError

        try:
            self._cliente.create_bucket(Bucket=self.bucket)
        except ClientError as error:
            if error.response["Error"]["Code"] != "BucketAlreadyOwnedByYou":
                raise

    def guardar(self, clave, archivo, tipo_mime):
        """Sube en flujo (por partes si es grande). Sin metadatos: ni nombre original ni RUT."""
        self._cliente.upload_fileobj(
            archivo, self.bucket, _comprobar(clave), ExtraArgs={"ContentType": tipo_mime}
        )

    def abrir(self, clave):
        return self._cliente.get_object(Bucket=self.bucket, Key=_comprobar(clave))["Body"]

    def existe(self, clave):
        from botocore.exceptions import ClientError

        try:
            self._cliente.head_object(Bucket=self.bucket, Key=_comprobar(clave))
        except ClientError as error:
            if error.response["ResponseMetadata"]["HTTPStatusCode"] == 404:
                return False
            raise
        return True

    def borrar(self, clave):
        """Borra el objeto. Que ya no exista no es un error, como en el almacenamiento local:
        S3 responde 204 en ese caso, pero Google Cloud Storage responde 404 (NoSuchKey)."""
        from botocore.exceptions import ClientError

        try:
            self._cliente.delete_object(Bucket=self.bucket, Key=_comprobar(clave))
        except ClientError as error:
            if error.response["ResponseMetadata"]["HTTPStatusCode"] != 404:
                raise

    def claves(self):
        paginas = self._cliente.get_paginator("list_objects_v2").paginate(Bucket=self.bucket)
        return sorted(objeto["Key"] for pagina in paginas for objeto in pagina.get("Contents", []))

    def url_firmada(self, clave, *, tipo_mime, disposicion, segundos):
        """URL de descarga firmada. El tipo y la disposición van dentro de la firma: quien
        reciba la URL no puede cambiarlos."""
        return self._cliente.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": _comprobar(clave),
                "ResponseContentType": tipo_mime,
                "ResponseContentDisposition": disposicion,
            },
            ExpiresIn=segundos,
        )


@functools.lru_cache(maxsize=4)
def _almacen_s3(bucket, endpoint_url, region, access_key_id, secret_access_key):
    return AlmacenS3(
        bucket=bucket,
        endpoint_url=endpoint_url,
        region=region,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
    )


def almacen():
    """El almacenamiento configurado en `DOCUMENTOS_ALMACENAMIENTO`."""
    tipo = settings.DOCUMENTOS_ALMACENAMIENTO
    if tipo == "local":
        return AlmacenLocal(settings.DOCUMENTOS_DIR)
    if tipo == "s3":
        return _almacen_s3(
            settings.S3_BUCKET,
            settings.S3_ENDPOINT_URL,
            settings.S3_REGION,
            settings.S3_ACCESS_KEY_ID,
            settings.S3_SECRET_ACCESS_KEY,
        )
    raise ImproperlyConfigured("DOCUMENTOS_ALMACENAMIENTO debe ser 'local' o 's3'.")


def segundos_de_url():
    return max(1, min(settings.DESCARGA_URL_SEGUNDOS, MAXIMO_URL_SEGUNDOS))


def entregar(clave, *, tipo_mime, disposicion):
    """Respuesta que entrega el archivo: redirección a una URL firmada de corta vida si el
    almacenamiento la ofrece (S3) o transmisión directa si no (local).

    Quien llama ya comprobó los permisos y registró el evento de auditoría (DOC-04).
    """
    destino = almacen()
    url = destino.url_firmada(
        clave, tipo_mime=tipo_mime, disposicion=disposicion, segundos=segundos_de_url()
    )
    if url:
        return HttpResponseRedirect(url)
    respuesta = FileResponse(destino.abrir(clave), content_type=tipo_mime)
    respuesta["Content-Disposition"] = disposicion
    respuesta["X-Content-Type-Options"] = "nosniff"
    # El archivo se abre aislado: aunque sea un PDF o una imagen con contenido activo, no
    # puede ejecutar nada ni leer nada en el dominio de la aplicación.
    respuesta["Content-Security-Policy"] = "sandbox"
    return respuesta
