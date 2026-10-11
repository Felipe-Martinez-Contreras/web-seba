"""Validación en el servidor de cada archivo subido (DOC-01, DOC-02, SEG-07).

El tipo que declara el navegador no se usa: el tipo real sale de la firma de bytes y, en
los formatos de Office, de la estructura OOXML. Sin dependencias externas (DEC-12).
"""

import hashlib
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath
from xml.etree import ElementTree

from django.conf import settings

_OOXML = "application/vnd.openxmlformats-officedocument."


@dataclass(frozen=True)
class Formato:
    extension: str  # la canónica: "jpeg" se guarda como "jpg"
    nombre: str  # como se le nombra a la persona
    familia: str  # ícono: pdf, word, excel, powerpoint o imagen
    tipo_mime: str
    firma: bytes
    # Solo en los formatos de Office: la parte principal del paquete y su tipo exacto.
    parte_principal: str = ""
    tipo_principal: str = ""


_PDF = Formato("pdf", "PDF", "pdf", "application/pdf", b"%PDF-")
_JPG = Formato("jpg", "JPG", "imagen", "image/jpeg", b"\xff\xd8\xff")
_PNG = Formato("png", "PNG", "imagen", "image/png", b"\x89PNG\r\n\x1a\n")
_ZIP = b"PK\x03\x04"
_DOCX = Formato(
    "docx",
    "DOCX",
    "word",
    _OOXML + "wordprocessingml.document",
    _ZIP,
    "word/document.xml",
    _OOXML + "wordprocessingml.document.main+xml",
)
_XLSX = Formato(
    "xlsx",
    "XLSX",
    "excel",
    _OOXML + "spreadsheetml.sheet",
    _ZIP,
    "xl/workbook.xml",
    _OOXML + "spreadsheetml.sheet.main+xml",
)
_PPTX = Formato(
    "pptx",
    "PPTX",
    "powerpoint",
    _OOXML + "presentationml.presentation",
    _ZIP,
    "ppt/presentation.xml",
    _OOXML + "presentationml.presentation.main+xml",
)

# Todo lo que la validación sabe comprobar. `DOCUMENTOS_FORMATOS` elige cuáles se admiten.
FORMATOS = {
    "pdf": _PDF,
    "docx": _DOCX,
    "xlsx": _XLSX,
    "pptx": _PPTX,
    "jpg": _JPG,
    "jpeg": _JPG,
    "png": _PNG,
}
FAMILIAS = {formato.extension: formato.familia for formato in FORMATOS.values()}
# Los únicos que "Ver" abre en el navegador (DOC-05).
VISIBLES_EN_NAVEGADOR = frozenset({"pdf", "jpg", "png"})

# Contenedor OLE2: .doc, .xls y .ppt, y también un .docx o .xlsx protegido con contraseña.
_OLE2 = b"\xd0\xcf\x11\xe0"

_TIPOS_DE_CONTENIDO = "[Content_Types].xml"
_MAXIMO_TIPOS_DE_CONTENIDO = 1024 * 1024
_MAXIMO_ENTRADAS = 5_000
_MAXIMO_DESCOMPRIMIDO = 500 * 1024 * 1024
_ESPACIO_XML = "{http://schemas.openxmlformats.org/package/2006/content-types}"

MOTIVO_VACIO = "El archivo está vacío."
MOTIVO_SIN_EXTENSION = "El archivo no tiene extensión, así que no se puede saber su formato."
MOTIVO_OFFICE_ANTIGUO = (
    "Los archivos de Office en formato antiguo o protegidos con contraseña no se admiten. "
    "Guárdelo como .docx, .xlsx o .pptx sin contraseña e intente de nuevo."
)
MOTIVO_MACROS = (
    "El archivo contiene macros, que no se admiten. Guárdelo sin macros como .docx, .xlsx "
    "o .pptx e intente de nuevo."
)
MOTIVO_DANADO = "El archivo está dañado o no es un documento de Office válido."


class ArchivoRechazado(Exception):
    """El archivo no cumple las reglas. `motivo` es el texto que se le muestra a la persona."""

    def __init__(self, motivo):
        super().__init__(motivo)
        self.motivo = motivo


@dataclass(frozen=True)
class ArchivoValidado:
    nombre: str  # nombre original saneado, con la extensión canónica
    titulo: str  # el nombre sin la extensión: título inicial del documento
    extension: str
    tipo_mime: str
    tamano: int
    sha256: str


def tamano_maximo():
    return settings.DOCUMENTOS_TAMANO_MAXIMO_MB * 1024 * 1024


def formatos_permitidos():
    """Extensión → formato, solo para las extensiones de la lista blanca configurada."""
    return {
        extension: FORMATOS[extension]
        for extension in (e.strip().lower().lstrip(".") for e in settings.DOCUMENTOS_FORMATOS)
        if extension in FORMATOS
    }


def nombres_de_formatos():
    """ "PDF, DOCX, XLSX, PPTX, JPG y PNG", según la lista blanca."""
    nombres = list(dict.fromkeys(formato.nombre for formato in formatos_permitidos().values()))
    if len(nombres) < 2:
        return "".join(nombres)
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


def _extension_de(nombre):
    """La última extensión, en minúsculas: de `informe.pdf.exe` cuenta `exe`."""
    _, punto, extension = nombre.rpartition(".")
    return extension.strip().lower() if punto else ""


def sanear_nombre(nombre, extension):
    """Nombre para guardar y para ofrecer en la descarga: sin rutas, sin caracteres de
    control ni reservados, con largo acotado y con la extensión ya validada. Las tildes y
    la ñ se conservan."""
    nombre = unicodedata.normalize("NFC", str(nombre)).replace("\\", "/").rsplit("/", 1)[-1]
    base, punto, _ = nombre.rpartition(".")
    base = base if punto else nombre
    # Categorías C*: caracteres de control y de formato, como el que invierte el texto.
    base = "".join(c for c in base if not unicodedata.category(c).startswith("C"))
    base = re.sub(r'[<>:"/\\|?*]', "_", base)
    base = " ".join(base.split()).strip(". ")[:120].strip(". ")
    return f"{base or 'documento'}.{extension}"


def _contenido_no_corresponde(formato):
    return ArchivoRechazado(f"El contenido no corresponde a un archivo {formato.nombre}.")


def _validar_ooxml(archivo, formato):
    """Estructura OOXML coherente con la extensión y sin macros."""
    archivo.seek(0)
    try:
        with zipfile.ZipFile(archivo) as paquete:
            entradas = paquete.infolist()
            if (
                len(entradas) > _MAXIMO_ENTRADAS
                or sum(entrada.file_size for entrada in entradas) > _MAXIMO_DESCOMPRIMIDO
                or any(entrada.flag_bits & 0x1 for entrada in entradas)  # entradas cifradas
            ):
                raise ArchivoRechazado(MOTIVO_DANADO)
            nombres = {entrada.filename for entrada in entradas}
            if any(PurePosixPath(nombre).name.lower() == "vbaproject.bin" for nombre in nombres):
                raise ArchivoRechazado(MOTIVO_MACROS)
            if _TIPOS_DE_CONTENIDO not in nombres or formato.parte_principal not in nombres:
                raise _contenido_no_corresponde(formato)
            if paquete.getinfo(_TIPOS_DE_CONTENIDO).file_size > _MAXIMO_TIPOS_DE_CONTENIDO:
                raise ArchivoRechazado(MOTIVO_DANADO)
            tipos_xml = paquete.read(_TIPOS_DE_CONTENIDO)
    except (zipfile.BadZipFile, zipfile.LargeZipFile, NotImplementedError, OSError, EOFError):
        raise ArchivoRechazado(MOTIVO_DANADO) from None

    # Un paquete de Office nunca declara un DOCTYPE ni entidades: así no se procesa ninguna.
    if b"<!DOCTYPE" in tipos_xml.upper() or b"<!ENTITY" in tipos_xml.upper():
        raise ArchivoRechazado(MOTIVO_DANADO)
    try:
        raiz = ElementTree.fromstring(tipos_xml)
    except ElementTree.ParseError:
        raise ArchivoRechazado(MOTIVO_DANADO) from None

    declarados = [elemento.get("ContentType", "").lower() for elemento in raiz.iter()]
    if any("macroenabled" in tipo or "vbaproject" in tipo for tipo in declarados):
        raise ArchivoRechazado(MOTIVO_MACROS)
    principal = next(
        (
            elemento.get("ContentType", "")
            for elemento in raiz.iter(_ESPACIO_XML + "Override")
            if elemento.get("PartName", "") == "/" + formato.parte_principal
        ),
        "",
    )
    if principal != formato.tipo_principal:
        raise _contenido_no_corresponde(formato)


def validar(archivo):
    """Comprueba el archivo subido y devuelve sus datos, o lanza `ArchivoRechazado`.

    `archivo` es un `UploadedFile` de Django. Al terminar queda posicionado al inicio.
    """
    if not archivo.size:
        raise ArchivoRechazado(MOTIVO_VACIO)
    if archivo.size > tamano_maximo():
        raise ArchivoRechazado(
            f"El archivo supera el tamaño máximo de {settings.DOCUMENTOS_TAMANO_MAXIMO_MB} MB."
        )

    archivo.seek(0)
    inicio = archivo.read(16)
    # Antes que la extensión: un .doc o .xls merece una explicación, no un "no permitido".
    if inicio.startswith(_OLE2):
        raise ArchivoRechazado(MOTIVO_OFFICE_ANTIGUO)

    extension = _extension_de(archivo.name or "")
    if not extension:
        raise ArchivoRechazado(MOTIVO_SIN_EXTENSION)
    formato = formatos_permitidos().get(extension)
    if formato is None:
        raise ArchivoRechazado(
            f"El formato .{extension[:10]} no está permitido. "
            f"Formatos admitidos: {nombres_de_formatos()}."
        )
    if not inicio.startswith(formato.firma):
        raise _contenido_no_corresponde(formato)
    if formato.parte_principal:
        _validar_ooxml(archivo, formato)

    archivo.seek(0)
    resumen = hashlib.sha256()
    tamano = 0
    for trozo in archivo.chunks():
        resumen.update(trozo)
        tamano += len(trozo)
    archivo.seek(0)
    if tamano != archivo.size:
        raise ArchivoRechazado(MOTIVO_DANADO)

    nombre = sanear_nombre(archivo.name or "", formato.extension)
    return ArchivoValidado(
        nombre=nombre,
        titulo=nombre.rpartition(".")[0],
        extension=formato.extension,
        tipo_mime=formato.tipo_mime,
        tamano=tamano,
        sha256=resumen.hexdigest(),
    )
