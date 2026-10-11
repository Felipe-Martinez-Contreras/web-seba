"""Archivos de prueba, generados en memoria: válidos de cada formato y los que deben rechazarse."""

import io
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile

_OOXML = "application/vnd.openxmlformats-officedocument."
_PARTES = {
    "docx": ("word/document.xml", _OOXML + "wordprocessingml.document.main+xml"),
    "xlsx": ("xl/workbook.xml", _OOXML + "spreadsheetml.sheet.main+xml"),
    "pptx": ("ppt/presentation.xml", _OOXML + "presentationml.presentation.main+xml"),
}
# Los mismos paquetes guardados con macros (DOCM, XLSM y PPTM).
_PARTES_CON_MACROS = {
    "docx": ("word/document.xml", "application/vnd.ms-word.document.macroEnabled.main+xml"),
    "xlsx": ("xl/workbook.xml", "application/vnd.ms-excel.sheet.macroEnabled.main+xml"),
    "pptx": (
        "ppt/presentation.xml",
        "application/vnd.ms-powerpoint.presentation.macroEnabled.main+xml",
    ),
}

BYTES_PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"
BYTES_JPG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"
BYTES_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89\x00\x00\x00\x00IEND\xaeB`\x82"
)
BYTES_EXE = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00" + b"\x00" * 64
BYTES_ELF = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 64
BYTES_HTML = b"<!doctype html><html><body><script>alert(document.domain)</script></body></html>"
BYTES_SVG = (
    b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
)
# Cabecera de un contenedor OLE2: .doc, .xls, .ppt o un .docx cifrado con contraseña.
BYTES_OLE2 = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 504


def archivo(nombre, contenido, tipo="application/octet-stream"):
    """Un archivo subido. El tipo declarado es arbitrario: el servidor no debe usarlo."""
    return SimpleUploadedFile(nombre, contenido, content_type=tipo)


def pdf(nombre="informe.pdf", relleno=b""):
    return archivo(nombre, BYTES_PDF + relleno, "application/pdf")


def pdf_de(tamano, nombre="grande.pdf"):
    """Un PDF válido de exactamente `tamano` bytes."""
    return archivo(nombre, BYTES_PDF + b"%" * (tamano - len(BYTES_PDF)))


def bytes_ooxml(formato, *, macros=False, vba=False, tipos=None, sin_tipos=False):
    """Paquete OOXML mínimo. `macros` declara el tipo con macros; `vba` agrega el proyecto VBA."""
    parte, tipo = (_PARTES_CON_MACROS if macros else _PARTES)[formato]
    if tipos is None:
        tipos = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" '
            'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f'<Override PartName="/{parte}" ContentType="{tipo}"/>'
            "</Types>"
        )
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as paquete:
        if not sin_tipos:
            paquete.writestr("[Content_Types].xml", tipos)
        paquete.writestr("_rels/.rels", "<Relationships/>")
        paquete.writestr(parte, "<contenido/>")
        if vba:
            paquete.writestr(parte.split("/")[0] + "/vbaProject.bin", b"\xd0\xcf\x11\xe0macro")
    return salida.getvalue()


def ooxml(formato, nombre=None, **opciones):
    return archivo(nombre or f"documento.{formato}", bytes_ooxml(formato, **opciones))


def zip_comun():
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as paquete:
        paquete.writestr("notas.txt", "un zip cualquiera")
    return salida.getvalue()


def validos():
    """Un archivo válido por cada formato permitido: (archivo, extensión, tipo MIME)."""
    return [
        (pdf("uno.pdf"), "pdf", "application/pdf"),
        (ooxml("docx"), "docx", _OOXML + "wordprocessingml.document"),
        (ooxml("xlsx"), "xlsx", _OOXML + "spreadsheetml.sheet"),
        (ooxml("pptx"), "pptx", _OOXML + "presentationml.presentation"),
        (archivo("foto.jpg", BYTES_JPG), "jpg", "image/jpeg"),
        (archivo("foto.JPEG", BYTES_JPG), "jpg", "image/jpeg"),
        (archivo("captura.png", BYTES_PNG), "png", "image/png"),
    ]
