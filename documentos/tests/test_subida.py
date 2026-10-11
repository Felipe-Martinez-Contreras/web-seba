"""Subida de documentos por el panel (ADM-08, DOC-02; prueba 10 y escenario E3)."""

import hashlib

import pytest

from auditoria.models import EventoAuditoria
from auditoria.services import Accion
from documentos import subida, validacion
from documentos.models import Documento, VersionDocumento
from documentos.tests import archivos

pytestmark = pytest.mark.django_db

OFFICE_ANTIGUO = (
    "Los archivos de Office en formato antiguo o protegidos con contraseña no se admiten. "
    "Guárdelo como .docx, .xlsx o .pptx sin contraseña e intente de nuevo."
)
NO_PERMITIDO = "no está permitido. Formatos admitidos: PDF, DOCX, XLSX, PPTX, JPG y PNG."

# Prueba 10 de la sección 12.2, más los casos vecinos: (nombre, contenido, motivo).
RECHAZADOS = [
    ("ejecutable.pdf", archivos.BYTES_EXE, "El contenido no corresponde a un archivo PDF."),
    ("ejecutable-linux.pdf", archivos.BYTES_ELF, "El contenido no corresponde a un archivo PDF."),
    ("pagina.pdf", archivos.BYTES_HTML, "El contenido no corresponde a un archivo PDF."),
    ("vacio.pdf", b"", "El archivo está vacío."),
    ("logo.svg", archivos.BYTES_SVG, "El formato .svg " + NO_PERMITIDO),
    ("logo.png", archivos.BYTES_SVG, "El contenido no corresponde a un archivo PNG."),
    (
        "macros.docm",
        archivos.bytes_ooxml("docx", macros=True, vba=True),
        "El formato .docm " + NO_PERMITIDO,
    ),
    ("macros.docx", archivos.bytes_ooxml("docx", macros=True, vba=True), validacion.MOTIVO_MACROS),
    ("macros.xlsx", archivos.bytes_ooxml("xlsx", macros=True, vba=True), validacion.MOTIVO_MACROS),
    ("antiguo.doc", archivos.BYTES_OLE2, OFFICE_ANTIGUO),
    ("con-clave.xlsx", archivos.BYTES_OLE2, OFFICE_ANTIGUO),
    ("comprimido.zip", archivos.zip_comun(), "El formato .zip " + NO_PERMITIDO),
    ("comprimido.docx", archivos.zip_comun(), "El contenido no corresponde a un archivo DOCX."),
]


def _subir(carpeta):
    return f"/panel/clientes/{carpeta.empresa_id}/carpetas/{carpeta.pk}/subir/"


def _carpeta(carpeta):
    return f"/panel/clientes/{carpeta.empresa_id}/carpetas/{carpeta.pk}/"


def _nada_guardado(almacen):
    return (
        not Documento.objects.exists()
        and not VersionDocumento.objects.exists()
        and almacen.claves() == []
        and not EventoAuditoria.objects.exists()
    )


@pytest.mark.parametrize(("nombre", "contenido", "motivo"), RECHAZADOS)
def test_prueba_10_un_archivo_invalido_se_rechaza_con_su_motivo_y_no_se_guarda_nada(
    cliente_http_admin, carpeta_a, almacen_de_prueba, nombre, contenido, motivo
):
    # El navegador lo declara como PDF: no importa.
    archivo = archivos.archivo(nombre, contenido, "application/pdf")
    respuesta = cliente_http_admin.post(_subir(carpeta_a), {"archivos": [archivo]})
    assert respuesta.status_code == 200
    pagina = respuesta.content.decode()
    assert "Rechazado." in pagina and motivo in pagina and nombre in pagina
    assert "Aceptado." not in pagina
    assert _nada_guardado(almacen_de_prueba)


def test_prueba_10_un_archivo_sobre_el_limite_se_rechaza(
    cliente_http_admin, carpeta_a, almacen_de_prueba, settings
):
    settings.DOCUMENTOS_TAMANO_MAXIMO_MB = 1
    grande = archivos.pdf_de(1024 * 1024 + 1)
    pagina = cliente_http_admin.post(_subir(carpeta_a), {"archivos": [grande]}).content.decode()
    assert "El archivo supera el tamaño máximo de 1 MB." in pagina
    assert _nada_guardado(almacen_de_prueba)
    # Justo en el límite sí entra.
    justo = archivos.pdf_de(1024 * 1024, "justo.pdf")
    pagina = cliente_http_admin.post(_subir(carpeta_a), {"archivos": [justo]}).content.decode()
    assert "Aceptado." in pagina
    assert VersionDocumento.objects.get().tamano == 1024 * 1024


def test_una_peticion_enorme_se_corta_antes_de_leer_el_archivo(
    cliente_http_admin, carpeta_a, almacen_de_prueba, settings
):
    """SEG-07: el tope por petición es de 4 archivos del tamaño máximo, más un margen."""
    assert subida.peticion_maxima() == 4 * 25 * 1024 * 1024 + 1024 * 1024
    settings.DOCUMENTOS_TAMANO_MAXIMO_MB = 1
    respuesta = cliente_http_admin.post(
        _subir(carpeta_a), {"archivos": [archivos.pdf()]}, CONTENT_LENGTH=str(6 * 1024 * 1024)
    )
    assert respuesta.status_code == 400
    assert "No pudimos procesar la solicitud" in respuesta.content.decode()
    assert _nada_guardado(almacen_de_prueba)


def test_e3_tres_archivos_uno_invalido_se_aceptan_dos_y_se_rechaza_uno_con_su_motivo(
    cliente_http_admin, administrador_activo, carpeta_a, empresa_a, almacen_de_prueba
):
    pagina = cliente_http_admin.get(_carpeta(carpeta_a)).content.decode()
    assert 'enctype="multipart/form-data"' in pagina and 'name="archivos"' in pagina
    assert (
        "Formatos admitidos: PDF, DOCX, XLSX, PPTX, JPG y PNG. Hasta 25 MB por archivo." in pagina
    )
    assert "Esta carpeta aún no tiene documentos" in pagina
    # El cliente que verá los archivos va destacado en la zona de subida, con su RUT.
    destino = pagina[pagina.index('id="subida-destino"') :][:1500]
    assert "Subiendo documentos para:" in destino
    assert "Empresa A de Prueba SpA" in destino and "RUT 76.111.111-6" in destino

    respuesta = cliente_http_admin.post(
        _subir(carpeta_a),
        {
            "archivos": [
                archivos.pdf("Matriz de riesgos 2026.pdf"),
                archivos.archivo("instalador.pdf", archivos.BYTES_EXE),
                archivos.ooxml("xlsx", "Inspección de extintores.xlsx"),
            ]
        },
    )
    pagina = respuesta.content.decode()
    assert pagina.count("Aceptado.") == 2 and pagina.count("Rechazado.") == 1
    # Cada archivo aceptado dice para qué cliente quedó publicado; el rechazado, no.
    assert pagina.count("Publicado para Empresa A de Prueba SpA.") == 2
    assert "El contenido no corresponde a un archivo PDF." in pagina

    # Efectos reales: dos documentos, dos objetos y dos eventos.
    documentos = list(Documento.objects.order_by("titulo"))
    assert [d.titulo for d in documentos] == ["Inspección de extintores", "Matriz de riesgos 2026"]
    assert all(d.empresa == empresa_a and d.carpeta == carpeta_a for d in documentos)
    assert len(almacen_de_prueba.claves()) == 2
    for documento in documentos:
        version = documento.version_vigente
        assert (version.numero, version.subido_por) == (1, administrador_activo)
        with almacen_de_prueba.abrir(version.clave) as guardado:
            assert hashlib.sha256(guardado.read()).hexdigest() == version.sha256
    xlsx = documentos[0].version_vigente
    assert (xlsx.extension, xlsx.nombre_original) == ("xlsx", "Inspección de extintores.xlsx")
    assert xlsx.tipo_mime.endswith("spreadsheetml.sheet")
    eventos = EventoAuditoria.objects.filter(accion=Accion.DOCUMENTO_SUBIDO)
    assert eventos.count() == 2 and EventoAuditoria.objects.count() == 2
    evento = eventos.get(objeto_uuid=documentos[1].pk)
    assert evento.actor == administrador_activo and evento.empresa == empresa_a
    assert evento.objeto_tipo == "documento"
    assert evento.detalle == "Matriz de riesgos 2026 (versión 1)"

    # La carpeta los lista, con enlace a su ficha.
    pagina = cliente_http_admin.get(_carpeta(carpeta_a)).content.decode()
    for documento in documentos:
        assert f"/panel/clientes/{empresa_a.pk}/documentos/{documento.pk}/" in pagina
    assert "instalador" not in pagina


def test_la_subida_con_javascript_recibe_solo_el_resultado_de_su_archivo(
    cliente_http_admin, carpeta_a, almacen_de_prueba
):
    """subida.js envía un archivo por petición, con el token CSRF en el encabezado."""
    aceptado = cliente_http_admin.post(
        _subir(carpeta_a),
        {"archivos": [archivos.pdf("uno.pdf")]},
        headers={"X-Subida": "fragmento"},
    )
    contenido = aceptado.content.decode().strip()
    documento = Documento.objects.get()
    assert contenido.startswith("<li") and contenido.endswith("</li>")
    assert "<html" not in contenido and "Aceptado." in contenido
    assert "Publicado para Empresa A de Prueba SpA." in contenido
    assert f"/documentos/{documento.pk}/" in contenido

    rechazado = cliente_http_admin.post(
        _subir(carpeta_a),
        {"archivos": [archivos.archivo("<b>negrita<b>.svg", archivos.BYTES_SVG)]},
        headers={"X-Subida": "fragmento"},
    )
    contenido = rechazado.content.decode()
    assert "Rechazado." in contenido and "El formato .svg" in contenido
    assert "Publicado para" not in contenido
    # El nombre que envió la persona se muestra escapado.
    assert "<b>" not in contenido and "&lt;b&gt;negrita&lt;b&gt;.svg" in contenido
    assert Documento.objects.count() == 1 and len(almacen_de_prueba.claves()) == 1


def test_la_pagina_de_la_carpeta_carga_el_script_de_subida_sin_codigo_en_linea(
    cliente_http_admin, carpeta_a
):
    pagina = cliente_http_admin.get(_carpeta(carpeta_a)).content.decode()
    assert '<script src="/static/js/subida.js" defer></script>' in pagina
    assert 'data-subida="subida-resultados"' in pagina
    # Al terminar, el script vuelve a cargar este bloque de la misma página.
    assert 'data-refresca="lista-documentos"' in pagina and 'id="lista-documentos"' in pagina
    assert f'data-maximo="{25 * 1024 * 1024}"' in pagina
    assert 'id="subida-resultados"' in pagina and "style=" not in pagina


def test_subir_exige_post_y_al_menos_un_archivo(cliente_http_admin, carpeta_a, almacen_de_prueba):
    assert cliente_http_admin.get(_subir(carpeta_a)).status_code == 405
    respuesta = cliente_http_admin.post(_subir(carpeta_a), follow=True)
    assert respuesta.redirect_chain == [(_carpeta(carpeta_a), 302)]
    assert "Seleccione al menos un archivo para subir." in respuesta.content.decode()
    assert _nada_guardado(almacen_de_prueba)


def test_no_se_sube_a_una_carpeta_por_la_url_de_otra_empresa(
    cliente_http_admin, carpeta_a, empresa_b, almacen_de_prueba
):
    url = f"/panel/clientes/{empresa_b.pk}/carpetas/{carpeta_a.pk}/subir/"
    assert cliente_http_admin.post(url, {"archivos": [archivos.pdf()]}).status_code == 404
    assert _nada_guardado(almacen_de_prueba)


def test_la_lista_de_documentos_pagina_de_a_25_sin_consultas_por_fila(
    cliente_http_admin, administrador_activo, carpeta_a, django_assert_max_num_queries
):
    """DOC-09."""
    from conftest import subir_documento

    for numero in range(27):
        subir_documento(carpeta_a, administrador_activo, archivos.pdf(f"Documento {numero:02}.pdf"))
    with django_assert_max_num_queries(12) as consultas:
        primera = cliente_http_admin.get(_carpeta(carpeta_a)).content.decode()
    assert primera.count('class="fila" href=') == 25 and "Página 1 de 2" in primera
    con_25 = len(consultas)
    segunda = cliente_http_admin.get(_carpeta(carpeta_a) + "?page=2").content.decode()
    assert segunda.count('class="fila" href=') == 2
    # Con 2 filas o con 25, la página hace las mismas consultas.
    with django_assert_max_num_queries(con_25):
        cliente_http_admin.get(_carpeta(carpeta_a) + "?page=2")


def test_la_subida_nombra_al_cliente_de_la_carpeta_y_no_a_otro(
    cliente_http_admin, carpeta_a, carpeta_b, empresa_b
):
    """Protección contra subir al cliente equivocado: la pantalla y cada resultado nombran
    al cliente dueño de la carpeta, con su razón social escapada."""
    empresa_b.razon_social = "Áridos <b>Ñuble</b> Ltda."
    empresa_b.save()
    pagina = cliente_http_admin.get(_carpeta(carpeta_b)).content.decode()
    destino = pagina[pagina.index('id="subida-destino"') :][:1500]
    assert "Áridos &lt;b&gt;Ñuble&lt;/b&gt; Ltda." in destino and "RUT 76.222.222-1" in destino
    assert "Empresa A de Prueba SpA" not in pagina
    assert 'aria-describedby="subida-destino subida-ayuda"' in pagina

    resultado = cliente_http_admin.post(
        _subir(carpeta_b), {"archivos": [archivos.pdf()]}, headers={"X-Subida": "fragmento"}
    ).content.decode()
    assert "Publicado para Áridos &lt;b&gt;Ñuble&lt;/b&gt; Ltda.." in resultado
    assert Documento.objects.get().empresa == empresa_b
