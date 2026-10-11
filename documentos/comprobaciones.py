"""Comprobaciones de la configuración del almacenamiento (`manage.py check`)."""

from pathlib import Path

from django.conf import settings
from django.core.checks import Error, register

from documentos.validacion import FORMATOS


def _dentro_de(ruta, carpeta):
    return ruta == carpeta or carpeta in ruta.parents


@register()
def almacenamiento_de_documentos(app_configs, **kwargs):
    errores = []
    tipo = settings.DOCUMENTOS_ALMACENAMIENTO
    if tipo == "local":
        destino = Path(settings.DOCUMENTOS_DIR).resolve()
        # SEG-07: los archivos subidos nunca quedan donde se sirven estáticos.
        publicas = [settings.BASE_DIR / "static", *settings.STATICFILES_DIRS]
        if getattr(settings, "STATIC_ROOT", None):
            publicas.append(settings.STATIC_ROOT)
        if any(_dentro_de(destino, Path(publica).resolve()) for publica in publicas):
            errores.append(
                Error(
                    "DOCUMENTOS_DIR está dentro de una carpeta de archivos estáticos.",
                    hint="Use una carpeta fuera del código y de STATIC_ROOT.",
                    id="documentos.E001",
                )
            )
    elif tipo == "s3":
        faltan = [
            nombre
            for nombre in ("S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY")
            if not getattr(settings, nombre)
        ]
        if faltan:
            errores.append(
                Error(
                    "Con DOCUMENTOS_ALMACENAMIENTO=s3 faltan: " + ", ".join(faltan) + ".",
                    id="documentos.E002",
                )
            )
    else:
        errores.append(
            Error("DOCUMENTOS_ALMACENAMIENTO debe ser 'local' o 's3'.", id="documentos.E003")
        )

    desconocidos = [
        extension
        for extension in settings.DOCUMENTOS_FORMATOS
        if extension.strip().lower().lstrip(".") not in FORMATOS
    ]
    if desconocidos:
        errores.append(
            Error(
                "DOCUMENTOS_FORMATOS incluye formatos que la validación no sabe comprobar: "
                + ", ".join(desconocidos)
                + ".",
                hint="Admitidos: " + ", ".join(FORMATOS) + ".",
                id="documentos.E004",
            )
        )
    if settings.DOCUMENTOS_TAMANO_MAXIMO_MB < 1:
        errores.append(Error("DOCUMENTOS_TAMANO_MAXIMO_MB debe ser 1 o más.", id="documentos.E005"))
    if settings.PAPELERA_DIAS < 1:
        errores.append(Error("PAPELERA_DIAS debe ser 1 o más.", id="documentos.E006"))
    return errores
