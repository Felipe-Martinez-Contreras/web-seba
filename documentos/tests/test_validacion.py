"""Validación de archivos en el servidor (DOC-01, DOC-02; prueba 10 de la sección 12.2)."""

import pytest

from documentos import validacion
from documentos.tests import archivos
from documentos.validacion import ArchivoRechazado

NO_ES_PDF = "El contenido no corresponde a un archivo PDF."
FORMATO_NO_PERMITIDO = "no está permitido. Formatos admitidos: PDF, DOCX, XLSX, PPTX, JPG y PNG."


def _motivo(archivo):
    with pytest.raises(ArchivoRechazado) as rechazo:
        validacion.validar(archivo)
    return rechazo.value.motivo


@pytest.mark.parametrize(("archivo", "extension", "tipo_mime"), archivos.validos())
def test_los_formatos_permitidos_se_aceptan_con_su_tipo_real(archivo, extension, tipo_mime):
    validado = validacion.validar(archivo)
    assert (validado.extension, validado.tipo_mime) == (extension, tipo_mime)
    assert validado.tamano == archivo.size
    assert len(validado.sha256) == 64
    assert validado.nombre.endswith("." + extension)
    # Queda al inicio, listo para guardarse.
    assert archivo.tell() == 0


def test_el_tipo_que_declara_el_navegador_no_cuenta():
    falso = archivos.archivo("virus.pdf", archivos.BYTES_EXE, "application/pdf")
    assert _motivo(falso) == NO_ES_PDF
    real = archivos.archivo("informe.pdf", archivos.BYTES_PDF, "application/x-msdownload")
    assert validacion.validar(real).tipo_mime == "application/pdf"


@pytest.mark.parametrize("contenido", [archivos.BYTES_EXE, archivos.BYTES_ELF])
def test_un_ejecutable_renombrado_como_pdf_se_rechaza(contenido):
    assert _motivo(archivos.archivo("factura.pdf", contenido)) == NO_ES_PDF


def test_un_html_renombrado_como_pdf_se_rechaza():
    assert _motivo(archivos.archivo("pagina.pdf", archivos.BYTES_HTML)) == NO_ES_PDF


def test_un_archivo_vacio_se_rechaza():
    assert _motivo(archivos.archivo("vacio.pdf", b"")) == "El archivo está vacío."


def test_el_limite_de_tamano_es_de_25_mb_por_defecto_y_se_aplica_al_byte(settings):
    assert validacion.tamano_maximo() == 25 * 1024 * 1024
    # Con el límite bajado a 1 MB, para no crear archivos de 25 MB en las pruebas.
    settings.DOCUMENTOS_TAMANO_MAXIMO_MB = 1
    limite = 1024 * 1024
    assert validacion.validar(archivos.pdf_de(limite)).tamano == limite
    assert _motivo(archivos.pdf_de(limite + 1)) == "El archivo supera el tamaño máximo de 1 MB."


def test_un_svg_se_rechaza_con_su_extension_y_tambien_disfrazado_de_png():
    assert _motivo(archivos.archivo("logo.svg", archivos.BYTES_SVG)) == (
        "El formato .svg " + FORMATO_NO_PERMITIDO
    )
    assert _motivo(archivos.archivo("logo.png", archivos.BYTES_SVG)) == (
        "El contenido no corresponde a un archivo PNG."
    )


@pytest.mark.parametrize(
    ("formato", "con_macros"), [("docx", "docm"), ("xlsx", "xlsm"), ("pptx", "pptm")]
)
def test_un_archivo_con_macros_se_rechaza_con_su_extension_y_renombrado(formato, con_macros):
    contenido = archivos.bytes_ooxml(formato, macros=True, vba=True)
    assert _motivo(archivos.archivo(f"planilla.{con_macros}", contenido)) == (
        f"El formato .{con_macros} " + FORMATO_NO_PERMITIDO
    )
    # El mismo archivo, renombrado al formato sin macros.
    assert _motivo(archivos.archivo(f"planilla.{formato}", contenido)) == validacion.MOTIVO_MACROS


def test_las_macros_se_detectan_por_el_tipo_declarado_o_por_el_proyecto_vba():
    solo_tipo = archivos.ooxml("docx", macros=True)
    assert _motivo(solo_tipo) == validacion.MOTIVO_MACROS
    # Declara el tipo normal, pero trae el proyecto VBA dentro.
    solo_vba = archivos.ooxml("docx", vba=True)
    assert _motivo(solo_vba) == validacion.MOTIVO_MACROS


@pytest.mark.parametrize("nombre", ["antiguo.doc", "antiguo.xls", "protegido.docx", "x.pdf"])
def test_office_antiguo_o_con_contrasena_recibe_un_motivo_claro(nombre):
    """La firma D0 CF 11 E0 manda sobre la extensión: .doc, .xls, .ppt o un .docx cifrado."""
    assert _motivo(archivos.archivo(nombre, archivos.BYTES_OLE2)) == (
        "Los archivos de Office en formato antiguo o protegidos con contraseña no se admiten. "
        "Guárdelo como .docx, .xlsx o .pptx sin contraseña e intente de nuevo."
    )


def test_un_zip_comun_renombrado_como_docx_se_rechaza():
    assert _motivo(archivos.archivo("comprimido.docx", archivos.zip_comun())) == (
        "El contenido no corresponde a un archivo DOCX."
    )
    assert _motivo(archivos.archivo("comprimido.zip", archivos.zip_comun())) == (
        "El formato .zip " + FORMATO_NO_PERMITIDO
    )


def test_la_estructura_ooxml_debe_coincidir_con_la_extension():
    assert _motivo(archivos.ooxml("docx", nombre="era-word.xlsx")) == (
        "El contenido no corresponde a un archivo XLSX."
    )
    assert _motivo(archivos.ooxml("docx", sin_tipos=True)) == (
        "El contenido no corresponde a un archivo DOCX."
    )


def test_una_plantilla_de_word_no_pasa_por_docx():
    tipos = (
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
        'officedocument.wordprocessingml.template.main+xml"/></Types>'
    )
    assert _motivo(archivos.ooxml("docx", tipos=tipos)) == (
        "El contenido no corresponde a un archivo DOCX."
    )


def test_un_zip_corrupto_o_con_entidades_xml_se_rechaza_como_danado():
    corrupto = archivos.bytes_ooxml("docx")[:60]
    assert _motivo(archivos.archivo("roto.docx", corrupto)) == validacion.MOTIVO_DANADO
    con_entidades = (
        '<?xml version="1.0"?><!DOCTYPE Types [<!ENTITY a "aaaa">]>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Override PartName="/word/document.xml" ContentType="&a;"/></Types>'
    )
    assert _motivo(archivos.ooxml("docx", tipos=con_entidades)) == validacion.MOTIVO_DANADO
    assert _motivo(archivos.ooxml("docx", tipos="<Types")) == validacion.MOTIVO_DANADO


def test_un_paquete_que_declara_demasiado_contenido_se_rechaza(monkeypatch):
    monkeypatch.setattr(validacion, "_MAXIMO_DESCOMPRIMIDO", 10)
    assert _motivo(archivos.ooxml("docx")) == validacion.MOTIVO_DANADO
    monkeypatch.undo()
    monkeypatch.setattr(validacion, "_MAXIMO_ENTRADAS", 2)
    assert _motivo(archivos.ooxml("docx")) == validacion.MOTIVO_DANADO


def test_solo_cuenta_la_ultima_extension_y_sin_extension_no_hay_formato():
    assert _motivo(archivos.archivo("informe.pdf.exe", archivos.BYTES_PDF)) == (
        "El formato .exe " + FORMATO_NO_PERMITIDO
    )
    assert _motivo(archivos.archivo("informe", archivos.BYTES_PDF)) == (
        validacion.MOTIVO_SIN_EXTENSION
    )
    assert _motivo(archivos.archivo("pagina.html", archivos.BYTES_HTML)) == (
        "El formato .html " + FORMATO_NO_PERMITIDO
    )
    # Un PDF real con extensión de imagen tampoco pasa.
    assert _motivo(archivos.archivo("informe.png", archivos.BYTES_PDF)) == (
        "El contenido no corresponde a un archivo PNG."
    )


def test_la_lista_blanca_es_configurable(settings):
    settings.DOCUMENTOS_FORMATOS = ["pdf"]
    assert validacion.validar(archivos.pdf()).extension == "pdf"
    assert _motivo(archivos.archivo("foto.png", archivos.BYTES_PNG)) == (
        "El formato .png no está permitido. Formatos admitidos: PDF."
    )


@pytest.mark.parametrize(
    ("original", "saneado"),
    [
        ("Matriz de riesgos — año 2026.PDF", "Matriz de riesgos — año 2026.pdf"),
        ("C:\\Users\\Ana\\Señalética.pdf", "Señalética.pdf"),
        ("../../etc/passwd.pdf", "passwd.pdf"),
        ('in<for>me: "final"?.pdf', "in_for_me_ _final__.pdf"),
        ("salto\nde\tlínea\x00.pdf", "saltodelínea.pdf"),
        ("factura\u202efdp.pdf", "facturafdp.pdf"),
        ("   .pdf", "documento.pdf"),
        ("a" * 300 + ".pdf", "a" * 120 + ".pdf"),
        # NFD (como lo envía macOS) se guarda compuesto.
        ("Inspeccio\u0301n.pdf", "Inspección.pdf"),
    ],
)
def test_el_nombre_original_se_sanea_conservando_tildes_y_enie(original, saneado):
    assert validacion.sanear_nombre(original, "pdf") == saneado
    validado = validacion.validar(archivos.pdf(original))
    assert validado.nombre == saneado
    assert validado.titulo == saneado.removesuffix(".pdf")
