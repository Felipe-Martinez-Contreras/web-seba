"""Pantallas del portal del cliente (CLI-01 a CLI-08, DOC-09)."""

import re

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from conftest import subir_documento
from documentos import services
from documentos.tests import archivos
from empresas.models import Carpeta
from portal.tests.conftest import enlaces, hoy

pytestmark = pytest.mark.django_db


def _ficha(documento, accion=""):
    return f"/portal/documentos/{documento.pk}/" + (f"{accion}/" if accion else "")


def _carpeta(carpeta):
    return f"/portal/carpetas/{carpeta.pk}/"


def _subir_varios(carpeta, administrador, cantidad, prefijo="Documento"):
    return [
        subir_documento(carpeta, administrador, archivos.pdf(f"{prefijo} {numero:02d}.pdf"))
        for numero in range(1, cantidad + 1)
    ]


def test_cli_01_el_inicio_muestra_saludo_empresa_buscador_carpetas_y_recientes(
    portal_a, administrador, carpeta_a, empresa_a
):
    documento = subir_documento(carpeta_a, administrador, archivos.pdf("Matriz de riesgos.pdf"))
    subir_documento(carpeta_a, administrador, archivos.ooxml("xlsx", "Inspección.xlsx"))
    respuesta = portal_a.get("/portal/")
    contenido = respuesta.content.decode()

    assert "Hola, Empresa A de Prueba SpA" in contenido and "RUT: 76.111.111-6" in contenido
    # Menú: Inicio, Carpetas y Mi cuenta, con Cerrar sesión; no existen Documentos ni Descargas.
    destinos = enlaces(respuesta)
    assert {"/portal/", "/portal/carpetas/", "/cuenta/"} <= set(destinos)
    assert 'href="/portal/" aria-current="page"' in contenido
    assert "Cerrar sesión" in contenido and "Descargas" not in contenido
    # Buscador en la barra superior y en el contenido, con el largo limitado.
    assert contenido.count('action="/portal/buscar/"') == 2
    assert contenido.count('maxlength="100"') == 2
    # Trato de usted.
    assert "Sus carpetas" in contenido and "Tus carpetas" not in contenido
    assert f'href="{_carpeta(carpeta_a)}"' in contenido
    assert f"2 documentos · Actualizado el {hoy()}" in contenido
    assert "Documentos recientes" in contenido
    assert f'href="{_ficha(documento)}"' in contenido and "Matriz de riesgos" in contenido
    assert contenido.count(">Nuevo<") == 2
    assert 'content="noindex"' in contenido


def test_cli_01_recientes_muestra_los_diez_ultimos_subidos_o_reemplazados(
    portal_a, administrador, carpeta_a
):
    documentos = _subir_varios(carpeta_a, administrador, 12)
    contenido = portal_a.get("/portal/").content.decode()
    recientes = contenido[contenido.index("Documentos recientes") :]
    orden = re.findall(r"Documento \d\d", recientes)
    assert orden == [f"Documento {numero:02d}" for numero in range(12, 2, -1)]

    # Un reemplazo vuelve a poner el documento primero.
    services.reemplazar(
        documentos[0], archivos.pdf("otro.pdf", b"% v2"), actor=administrador, request=None
    )
    contenido = portal_a.get("/portal/").content.decode()
    recientes = contenido[contenido.index("Documentos recientes") :]
    assert re.findall(r"Documento \d\d", recientes)[0] == "Documento 01"


def test_cli_01_la_etiqueta_nuevo_dura_catorce_dias(
    portal_a, documento_a, carpeta_a, avanzar_el_reloj
):
    paginas = ("/portal/", _carpeta(carpeta_a), _ficha(documento_a), "/portal/buscar/?q=informe")
    for ruta in paginas:
        assert ">Nuevo<" in portal_a.get(ruta).content.decode(), ruta
    avanzar_el_reloj(days=13, hours=23)
    assert ">Nuevo<" in portal_a.get("/portal/").content.decode()
    avanzar_el_reloj(days=14)
    for ruta in paginas:
        assert ">Nuevo<" not in portal_a.get(ruta).content.decode(), ruta


def test_cli_06_sin_documentos_el_inicio_muestra_un_estado_vacio_neutro(portal_a, carpeta_a):
    contenido = portal_a.get("/portal/").content.decode()
    assert "Aún no hay documentos disponibles" in contenido
    assert "Documentos recientes" not in contenido and 'id="buscador-portal"' not in contenido
    # Las carpetas sí se ven, con su contador en cero y sin fecha.
    assert "Carpeta de A" in contenido and "0 documentos" in contenido
    assert "Actualizado el" not in contenido

    carpeta_a.delete()
    contenido = portal_a.get("/portal/").content.decode()
    assert "Aún no hay documentos disponibles" in contenido and "Sus carpetas" not in contenido
    assert "Aún no hay carpetas" in portal_a.get("/portal/carpetas/").content.decode()


def test_cli_06_el_estado_vacio_muestra_el_contacto_del_profesional(portal_a, carpeta_a, negocio):
    """CLI-06: con datos registrados en DatosNegocio, el cliente sabe a quién pedirle sus
    documentos."""
    contenido = portal_a.get("/portal/").content.decode()
    assert "Aún no hay documentos disponibles" in contenido
    assert "¿Necesita un documento?" in contenido
    assert "Puede contactar a Prevención de Prueba:" in contenido
    assert 'href="tel:+56987654321"' in contenido and "+56 9 8765 4321" in contenido
    assert 'href="mailto:contacto@prevencion-de-prueba.cl"' in contenido
    assert "Lunes a viernes, de 9:00 a 18:00" in contenido

    negocio.whatsapp = "+56 9 5555 6666"
    negocio.nombre_comercial = ""
    negocio.save()
    contenido = portal_a.get("/portal/").content.decode()
    assert "Puede contactarnos:" in contenido
    assert 'href="https://wa.me/56955556666"' in contenido


def test_cli_06_sin_contacto_registrado_el_estado_vacio_no_muestra_marcadores(
    portal_a, carpeta_a, negocio
):
    """Con los datos en [COMPLETAR] o vacíos, queda el texto neutro y nada más (R2)."""
    for telefono, correo in (("", ""), ("[COMPLETAR]", "[COMPLETAR]")):
        negocio.telefono, negocio.email_publico = telefono, correo
        negocio.save()
        contenido = portal_a.get("/portal/").content.decode()
        assert "Aún no hay documentos disponibles" in contenido
        assert "¿Necesita un documento?" not in contenido
        assert "COMPLETAR" not in contenido and "mailto:" not in contenido


def test_cli_06_con_documentos_el_contacto_no_se_muestra_ni_se_consulta(
    portal_a, carpeta_a, administrador, negocio
):
    subir_documento(carpeta_a, administrador)
    contenido = portal_a.get("/portal/").content.decode()
    assert "¿Necesita un documento?" not in contenido
    assert "contacto@prevencion-de-prueba.cl" not in contenido


def test_la_lista_de_carpetas_respeta_el_orden_del_administrador(
    portal_a, administrador, carpeta_a, empresa_a
):
    Carpeta.objects.create(empresa=empresa_a, nombre="Zeta va primero", orden=0)
    subir_documento(carpeta_a, administrador)
    respuesta = portal_a.get("/portal/carpetas/")
    contenido = respuesta.content.decode()
    assert contenido.index("Zeta va primero") < contenido.index("Carpeta de A")
    assert "1 documento ·" in contenido and "0 documentos" in contenido
    assert 'href="/portal/carpetas/" aria-current="page"' in contenido


def test_cli_02_la_carpeta_lista_sus_documentos_con_ver_y_descargar(
    portal_a, administrador, carpeta_a
):
    pdf = subir_documento(carpeta_a, administrador, archivos.pdf("Beta manual.pdf"))
    planilla = subir_documento(carpeta_a, administrador, archivos.ooxml("xlsx", "Alfa.xlsx"))
    respuesta = portal_a.get(_carpeta(carpeta_a))
    contenido = respuesta.content.decode()

    assert "<h1" in contenido and "Carpeta de A" in contenido
    # Migas: Carpetas › carpeta.
    assert 'href="/portal/carpetas/"' in contenido
    # Título, tipo, tamaño y fecha de cada documento.
    assert f"PDF · {len(archivos.BYTES_PDF)}\xa0bytes · Actualizado el {hoy()}" in contenido
    assert "XLSX ·" in contenido
    for documento in (pdf, planilla):
        assert f'href="{_ficha(documento)}"' in contenido
        assert f'href="{_ficha(documento, "descargar")}"' in contenido
    # "Ver" solo donde el navegador puede mostrarlo, y en una pestaña nueva.
    assert f'href="{_ficha(pdf, "ver")}" target="_blank" rel="noopener"' in contenido
    assert _ficha(planilla, "ver") not in contenido

    # Orden: por fecha (lo último primero) o por nombre.
    assert contenido.index("Alfa") < contenido.index("Beta manual")
    assert 'aria-current="page">Más recientes<' in contenido
    por_nombre = portal_a.get(_carpeta(carpeta_a) + "?orden=nombre").content.decode()
    assert por_nombre.index("Alfa") < por_nombre.index("Beta manual")
    assert 'aria-current="page">Por nombre<' in por_nombre
    services.reemplazar(pdf, archivos.pdf("v2.pdf", b"% v2"), actor=administrador, request=None)
    contenido = portal_a.get(_carpeta(carpeta_a)).content.decode()
    assert contenido.index("Beta manual") < contenido.index("Alfa")
    # Un orden desconocido no rompe la página: usa el predeterminado.
    otro = portal_a.get(_carpeta(carpeta_a) + "?orden=;drop").content.decode()
    assert otro.index("Beta manual") < otro.index("Alfa")


def test_cli_02_una_carpeta_sin_documentos_lo_explica(portal_a, carpeta_a):
    contenido = portal_a.get(_carpeta(carpeta_a)).content.decode()
    assert "Esta carpeta aún no tiene documentos" in contenido
    assert "Ver las carpetas" in contenido and "Por nombre" not in contenido


def test_doc_09_la_carpeta_pagina_de_a_25_y_conserva_el_orden(portal_a, administrador, carpeta_a):
    _subir_varios(carpeta_a, administrador, 30)
    primera = portal_a.get(_carpeta(carpeta_a) + "?orden=nombre").content.decode()
    assert primera.count("/descargar/") == 25 and "Página 1 de 2" in primera
    assert 'href="?orden=nombre&amp;page=2"' in primera
    segunda = portal_a.get(_carpeta(carpeta_a) + "?orden=nombre&page=2").content.decode()
    assert segunda.count("/descargar/") == 5 and "Documento 30" in segunda
    # Una página inválida cae en la más cercana.
    assert "Página 2 de 2" in portal_a.get(_carpeta(carpeta_a) + "?page=99").content.decode()


def test_cli_03_la_busqueda_por_titulo_ignora_mayusculas_y_tildes(
    portal_a, administrador, carpeta_a
):
    documento = subir_documento(
        carpeta_a, administrador, archivos.ooxml("xlsx", "Inspección de extintores.xlsx")
    )
    subir_documento(carpeta_a, administrador, archivos.pdf("Matriz de riesgos.pdf"))
    for texto in ("inspeccion", "INSPECCIÓN", "  extintores  ", "ón de ext"):
        respuesta = portal_a.get("/portal/buscar/", {"q": texto})
        contenido = respuesta.content.decode()
        assert "1 resultado para" in contenido, texto
        assert f'href="{_ficha(documento)}"' in contenido
        assert f'href="{_ficha(documento, "descargar")}"' in contenido
        assert "Matriz de riesgos" not in contenido
        # Cada resultado dice en qué carpeta está.
        assert "Carpeta: Carpeta de A" in contenido
    # El texto buscado queda en los dos buscadores de la página.
    assert contenido.count('value="ón de ext"') == 2
    assert "2 resultados para" in portal_a.get("/portal/buscar/?q=i").content.decode()


def test_cli_03_sin_resultados_y_sin_texto_tienen_su_propio_estado(portal_a, documento_a):
    contenido = portal_a.get("/portal/buscar/?q=inexistente").content.decode()
    assert "Sin resultados para «inexistente»" in contenido
    assert "Pruebe con otra palabra" in contenido and "/descargar/" not in contenido
    for ruta in ("/portal/buscar/", "/portal/buscar/?q=", "/portal/buscar/?q=%20%20"):
        contenido = portal_a.get(ruta).content.decode()
        assert "Escriba qué documento busca" in contenido, ruta
        assert "Sin resultados" not in contenido and "/descargar/" not in contenido


def test_cli_03_el_texto_de_busqueda_se_limita_a_100_caracteres(portal_a, administrador, carpeta_a):
    cien = "a" * 100
    subir_documento(carpeta_a, administrador, archivos.pdf(cien + ".pdf"))
    # Lo que pasa de 100 caracteres no se usa: con el texto completo no habría resultados.
    respuesta = portal_a.get("/portal/buscar/", {"q": cien + "zzz" * 50})
    contenido = respuesta.content.decode()
    assert "1 resultado para" in contenido and "zzz" not in contenido
    assert contenido.count(f'value="{cien}"') == 2
    assert contenido.count('maxlength="100"') == 2
    largo = portal_a.get("/portal/buscar/", {"q": "b" * 5000}).content.decode()
    assert f"Sin resultados para «{'b' * 100}»" in largo and "b" * 101 not in largo


@pytest.mark.parametrize(
    ("texto", "escapado", "prohibido"),
    [
        (
            "<script>alert(1)</script>",
            "&lt;script&gt;alert(1)&lt;/script&gt;",
            "<script>alert(1)",
        ),
        (
            '"><img src=x onerror=alert(1)>',
            "&quot;&gt;&lt;img src=x onerror=alert(1)&gt;",
            "<img src=x",
        ),
    ],
)
def test_cli_03_una_busqueda_con_html_se_muestra_escapada_y_no_se_ejecuta(
    portal_a, documento_a, texto, escapado, prohibido
):
    """SEG-06: el texto que escribe la persona vuelve a la página solo como texto."""
    respuesta = portal_a.get("/portal/buscar/", {"q": texto})
    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert f"Sin resultados para «{escapado}»" in contenido
    # También dentro del atributo `value` de los dos buscadores.
    assert contenido.count(f'value="{escapado}"') == 2
    assert prohibido not in contenido
    # Los únicos scripts de la página son archivos propios: ninguno va en línea.
    scripts = re.findall(r"<script[^>]*>", contenido)
    assert scripts and all(re.fullmatch(r'<script src="/static/[^"]+" defer>', s) for s in scripts)
    # Y aunque llegara a la página, la política del sitio no ejecuta scripts en línea.
    politica = respuesta["Content-Security-Policy"]
    assert "script-src 'self'" in politica and "unsafe-inline" not in politica


def test_cli_08_la_ficha_muestra_los_datos_y_los_botones_sin_visor_incrustado(
    portal_a, administrador, documento_a, carpeta_a
):
    services.editar(
        documento_a,
        titulo="Informe anual",
        descripcion="Primera línea\nSegunda <b>línea</b>",
        actor=administrador,
        request=None,
    )
    contenido = portal_a.get(_ficha(documento_a)).content.decode()
    # Migas: Carpetas › carpeta › documento.
    assert 'href="/portal/carpetas/"' in contenido
    assert f'href="{_carpeta(carpeta_a)}"' in contenido
    assert 'aria-current="page">Informe anual<' in contenido
    assert "<h1" in contenido and "PDF:" in contenido
    assert f"PDF · {len(archivos.BYTES_PDF)}\xa0bytes · Actualizado el {hoy()}" in contenido
    # La descripción conserva los saltos de línea y va escapada.
    assert "Primera línea<br>Segunda &lt;b&gt;línea&lt;/b&gt;" in contenido
    assert f'href="{_ficha(documento_a, "descargar")}"' in contenido
    assert f'href="{_ficha(documento_a, "ver")}" target="_blank" rel="noopener"' in contenido
    assert "Ver en pantalla" in contenido
    for etiqueta in ("<iframe", "<embed", "<object"):
        assert etiqueta not in contenido


def test_cli_08_un_archivo_que_no_se_ve_en_el_navegador_solo_ofrece_descargar(
    portal_a, administrador, carpeta_a
):
    documento = subir_documento(carpeta_a, administrador, archivos.ooxml("docx"))
    contenido = portal_a.get(_ficha(documento)).content.decode()
    assert _ficha(documento, "descargar") in contenido
    assert _ficha(documento, "ver") not in contenido and "Ver en pantalla" not in contenido
    assert "descárguelo para abrirlo" in contenido


def test_cli_05_el_cliente_no_ve_versiones_ni_acciones_de_edicion(
    portal_a, administrador, documento_a, carpeta_a, empresa_a
):
    empresa_a.notas_internas = "Nota interna que el cliente no debe ver"
    empresa_a.save()
    services.reemplazar(
        documento_a, archivos.pdf("corregido.pdf", b"% v2"), actor=administrador, request=None
    )
    rutas = (
        "/portal/",
        "/portal/carpetas/",
        _carpeta(carpeta_a),
        _ficha(documento_a),
        "/portal/buscar/?q=informe",
        "/cuenta/",
    )
    for ruta in rutas:
        respuesta = portal_a.get(ruta)
        contenido = respuesta.content.decode()
        assert respuesta.status_code == 200, ruta
        for texto in (
            "Versión",
            "Historial",
            "Papelera",
            "Nota interna",
            "informe.pdf",
            "corregido.pdf",
            "Editar",
            "Eliminar",
            "Reemplazar",
            "Subir",
            "/panel/",
            "/versiones/",
            'type="file"',
        ):
            assert texto not in contenido, (ruta, texto)
        # El único formulario que modifica algo es el de cerrar sesión, que está en el menú
        # de escritorio y en el móvil (y, en Mi cuenta, el cambio de contraseña).
        formularios = re.findall(r'<form[^>]*method="post"[^>]*>', contenido)
        ajenos = [formulario for formulario in formularios if 'action="/salir/"' not in formulario]
        assert len(formularios) - len(ajenos) == 2, ruta
        assert len(ajenos) == (1 if ruta == "/cuenta/" else 0), ruta


def test_cli_04_mi_cuenta_usa_la_estructura_del_portal(portal_a, cliente_a_activo):
    respuesta = portal_a.get("/cuenta/")
    contenido = respuesta.content.decode()
    assert "Cliente de A" in contenido and "11.111.111-1" in contenido
    assert "cliente.a@ejemplo.test" in contenido and "Cambiar contraseña" in contenido
    assert {"/portal/", "/portal/carpetas/"} <= set(enlaces(respuesta))
    assert 'href="/cuenta/" aria-current="page"' in contenido
    assert 'action="/portal/buscar/"' in contenido
    assert 'action="/salir/"' in contenido and "Cerrar sesión" in contenido


def _consultas(cliente_http, ruta):
    with CaptureQueriesContext(connection) as consultas:
        assert cliente_http.get(ruta).status_code == 200
    return len(consultas)


def test_doc_09_los_listados_del_portal_no_consultan_por_fila(
    portal_a, administrador, carpeta_a, empresa_a
):
    documento = subir_documento(carpeta_a, administrador, archivos.pdf("Documento 00.pdf"))
    rutas = ("/portal/", "/portal/carpetas/", _carpeta(carpeta_a), "/portal/buscar/?q=documento")
    con_uno = {ruta: _consultas(portal_a, ruta) for ruta in rutas}
    for orden in range(2, 6):
        Carpeta.objects.create(empresa=empresa_a, nombre=f"Carpeta {orden}", orden=orden)
    _subir_varios(carpeta_a, administrador, 29)
    assert {ruta: _consultas(portal_a, ruta) for ruta in rutas} == con_uno
    assert _consultas(portal_a, _ficha(documento)) <= max(con_uno.values())


def test_cli_07_cualquier_documento_queda_a_dos_clics_del_inicio(
    portal_a, administrador, carpeta_a, empresa_a
):
    """Clic 1: la carpeta (o enviar la búsqueda). Clic 2: el documento o su descarga."""
    otra = Carpeta.objects.create(empresa=empresa_a, nombre="Otra carpeta", orden=2)
    documentos = _subir_varios(carpeta_a, administrador, 30)
    documentos += _subir_varios(otra, administrador, 3, prefijo="Protocolo")

    inicio = enlaces(portal_a.get("/portal/"))
    # El buscador está en el inicio: enviarlo es el primer clic.
    assert 'action="/portal/buscar/"' in portal_a.get("/portal/").content.decode()
    por_carpeta, por_buscador = 0, 0
    paginas = {}
    for documento in documentos:
        carpeta = _carpeta(documento.carpeta)
        assert carpeta in inicio
        if carpeta not in paginas:
            paginas[carpeta] = enlaces(portal_a.get(carpeta))
        segundo_clic = paginas[carpeta]
        if _ficha(documento) in segundo_clic:
            por_carpeta += 1
        else:
            # Quedó en la segunda página de su carpeta: se llega por el buscador.
            segundo_clic = enlaces(portal_a.get("/portal/buscar/", {"q": documento.titulo}))
            por_buscador += 1
        assert _ficha(documento) in segundo_clic, documento.titulo
        assert _ficha(documento, "descargar") in segundo_clic, documento.titulo
    assert (por_carpeta, por_buscador) == (28, 5)
    # Los diez más recientes, además, están a un solo clic.
    assert sum(_ficha(documento) in inicio for documento in documentos) == 10
