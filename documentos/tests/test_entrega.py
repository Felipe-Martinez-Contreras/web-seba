"""Ver y descargar (DOC-04, DOC-05): permisos, auditoría, encabezados y URL firmada."""

import logging
from urllib.parse import parse_qs, urlsplit

import pytest
from django.test import Client

from auditoria.models import EventoAuditoria
from auditoria.services import Accion
from conftest import RUT_CLIENTE_A, entrar, subir_documento
from documentos import almacenamiento, services
from documentos.tests import archivos

pytestmark = pytest.mark.django_db

ENTREGAS = (Accion.DOCUMENTO_VISTO, Accion.DOCUMENTO_DESCARGADO)


@pytest.fixture
def portal_a(cliente_a_activo):
    cliente = Client()
    entrar(cliente, RUT_CLIENTE_A)
    return cliente


def _portal(documento, accion):
    return f"/portal/documentos/{documento.pk}/{accion}/"


def _panel(documento, version, accion):
    return (
        f"/panel/clientes/{documento.empresa_id}/documentos/{documento.pk}"
        f"/versiones/{version.pk}/{accion}/"
    )


def _cuerpo(respuesta):
    return b"".join(respuesta.streaming_content)


def test_descargar_entrega_el_archivo_como_adjunto_y_registra_el_evento(
    portal_a, cliente_a_activo, documento_a, empresa_a
):
    respuesta = portal_a.get(_portal(documento_a, "descargar"), REMOTE_ADDR="203.0.113.9")
    assert respuesta.status_code == 200
    assert _cuerpo(respuesta) == archivos.BYTES_PDF
    assert respuesta["Content-Type"] == "application/pdf"
    assert respuesta["Content-Disposition"] == 'attachment; filename="informe.pdf"'
    assert respuesta["Content-Length"] == str(len(archivos.BYTES_PDF))
    assert respuesta["X-Content-Type-Options"] == "nosniff"
    # El archivo se abre aislado del dominio de la aplicación.
    assert respuesta["Content-Security-Policy"] == "sandbox"
    assert "no-store" in respuesta["Cache-Control"]

    evento = EventoAuditoria.objects.get(accion=Accion.DOCUMENTO_DESCARGADO)
    assert evento.actor == cliente_a_activo and evento.empresa == empresa_a
    assert (evento.objeto_tipo, evento.objeto_uuid) == ("documento", documento_a.pk)
    assert evento.ip == "203.0.113.9" and evento.detalle == "informe (versión 1)"
    assert not EventoAuditoria.objects.filter(accion=Accion.DOCUMENTO_VISTO).exists()


@pytest.mark.parametrize(
    ("archivo", "tipo_mime", "en_linea"),
    [
        (archivos.pdf("manual.pdf"), "application/pdf", True),
        (archivos.archivo("foto.jpg", archivos.BYTES_JPG), "image/jpeg", True),
        (archivos.archivo("captura.png", archivos.BYTES_PNG), "image/png", True),
        (archivos.ooxml("docx"), None, False),
        (archivos.ooxml("xlsx"), None, False),
        (archivos.ooxml("pptx"), None, False),
    ],
)
def test_ver_abre_en_el_navegador_solo_pdf_jpg_y_png(
    portal_a, carpeta_a, administrador, archivo, tipo_mime, en_linea
):
    documento = subir_documento(carpeta_a, administrador, archivo)
    respuesta = portal_a.get(_portal(documento, "ver"))
    assert respuesta.status_code == 200
    disposicion = respuesta["Content-Disposition"]
    assert disposicion.startswith("inline" if en_linea else "attachment")
    assert respuesta["Content-Type"] == (tipo_mime or documento.version_vigente.tipo_mime)
    assert respuesta["Content-Security-Policy"] == "sandbox"
    # El evento dice lo que ocurrió: verlo en pantalla, o una descarga si no se puede ver.
    esperado = Accion.DOCUMENTO_VISTO if en_linea else Accion.DOCUMENTO_DESCARGADO
    assert EventoAuditoria.objects.get(accion__in=ENTREGAS).accion == esperado
    # Descargar siempre es adjunto, también un PDF.
    assert portal_a.get(_portal(documento, "descargar"))["Content-Disposition"].startswith(
        "attachment"
    )


def test_el_nombre_descargado_conserva_tildes_y_enie_segun_rfc_6266(
    portal_a, carpeta_a, administrador
):
    documento = subir_documento(
        carpeta_a, administrador, archivos.pdf("Señalética de emergencia — año 2026.pdf")
    )
    disposicion = portal_a.get(_portal(documento, "descargar"))["Content-Disposition"]
    assert disposicion == (
        "attachment; filename*=utf-8''Se%C3%B1al%C3%A9tica%20de%20emergencia%20%E2%80%94%20"
        "a%C3%B1o%202026.pdf"
    )
    # Un nombre con comillas no rompe el encabezado: se saneó al subir.
    raro = subir_documento(carpeta_a, administrador, archivos.pdf('a"b\r\nX-Otro: 1.pdf'))
    disposicion = portal_a.get(_portal(raro, "descargar"))["Content-Disposition"]
    assert "\n" not in disposicion and "\r" not in disposicion
    assert disposicion == 'attachment; filename="a_bX-Otro_ 1.pdf"'


def test_ver_y_descargar_son_solo_get(portal_a, documento_a):
    for accion in ("ver", "descargar"):
        assert portal_a.post(_portal(documento_a, accion)).status_code == 405
    assert not EventoAuditoria.objects.filter(accion__in=ENTREGAS).exists()


def test_sin_sesion_no_hay_entrega(documento_a):
    cliente = Client()
    for accion in ("ver", "descargar"):
        ruta = _portal(documento_a, accion)
        respuesta = cliente.get(ruta)
        assert (respuesta.status_code, respuesta["Location"]) == (302, f"/acceso/?next={ruta}")
    assert not EventoAuditoria.objects.filter(accion=Accion.DOCUMENTO_DESCARGADO).exists()


def test_el_cliente_recibe_siempre_la_version_vigente_y_el_administrador_cualquiera(
    portal_a, cliente_http_admin, administrador_activo, documento_a
):
    """DOC-08 y E4."""
    primera = documento_a.version_vigente
    nuevo = archivos.BYTES_PDF + b"% segunda version\n"
    segunda = services.reemplazar(
        documento_a,
        archivos.archivo("informe-corregido.pdf", nuevo),
        actor=administrador_activo,
        request=None,
    )
    respuesta = portal_a.get(_portal(documento_a, "descargar"))
    assert _cuerpo(respuesta) == nuevo
    assert respuesta["Content-Disposition"] == 'attachment; filename="informe-corregido.pdf"'

    # El administrador descarga ambas desde el historial.
    assert _cuerpo(cliente_http_admin.get(_panel(documento_a, primera, "descargar"))) == (
        archivos.BYTES_PDF
    )
    respuesta = cliente_http_admin.get(_panel(documento_a, segunda, "ver"))
    assert _cuerpo(respuesta) == nuevo and respuesta["Content-Disposition"].startswith("inline")
    detalles = set(
        EventoAuditoria.objects.filter(actor=administrador_activo).values_list("accion", "detalle")
    )
    assert (Accion.DOCUMENTO_DESCARGADO, "informe (versión 1)") in detalles
    assert (Accion.DOCUMENTO_VISTO, "informe (versión 2)") in detalles


def test_una_version_solo_se_alcanza_bajo_su_documento_y_su_empresa(
    cliente_http_admin, documento_a, documento_b, empresa_b
):
    version_a = documento_a.version_vigente
    cruzadas = [
        # La versión de A pedida bajo el documento de B.
        _panel(documento_b, version_a, "descargar"),
        # El documento de A pedido bajo la empresa de B.
        f"/panel/clientes/{empresa_b.pk}/documentos/{documento_a.pk}"
        f"/versiones/{version_a.pk}/descargar/",
    ]
    for ruta in cruzadas:
        assert cliente_http_admin.get(ruta).status_code == 404
    assert not EventoAuditoria.objects.filter(accion=Accion.DOCUMENTO_DESCARGADO).exists()


def test_si_falta_el_archivo_responde_404_y_no_queda_evento(
    portal_a, documento_a, almacen_de_prueba
):
    almacen_de_prueba.borrar(documento_a.version_vigente.clave)
    assert portal_a.get(_portal(documento_a, "descargar")).status_code == 404
    assert not EventoAuditoria.objects.filter(accion=Accion.DOCUMENTO_DESCARGADO).exists()


def test_si_la_auditoria_falla_no_se_entrega_el_archivo(portal_a, documento_a, monkeypatch):
    def fallar(*args, **kwargs):
        raise RuntimeError("fallo simulado al registrar")

    entregas = []
    monkeypatch.setattr(services, "registrar", fallar)
    monkeypatch.setattr(almacenamiento, "entregar", lambda *a, **k: entregas.append(a))
    portal_a.raise_request_exception = False
    assert portal_a.get(_portal(documento_a, "descargar")).status_code == 500
    assert entregas == []


def test_con_s3_la_entrega_es_una_redireccion_a_una_url_firmada_de_dos_minutos(
    almacen_s3, cliente_a_activo, carpeta_a, administrador, settings
):
    """El mismo código de descarga que en local: solo cambia la respuesta final (DOC-04)."""
    settings.DESCARGA_URL_SEGUNDOS = 900  # aunque se configure más, el tope es 120
    documento = subir_documento(carpeta_a, administrador, archivos.pdf("Señalética.pdf"))
    portal = Client()
    entrar(portal, RUT_CLIENTE_A)

    respuesta = portal.get(_portal(documento, "ver"))
    assert respuesta.status_code == 302
    destino = urlsplit(respuesta["Location"])
    consulta = parse_qs(destino.query)
    assert destino.path.endswith("/" + documento.version_vigente.clave)
    assert consulta["X-Amz-Expires"] == ["120"]
    assert consulta["response-content-type"] == ["application/pdf"]
    assert consulta["response-content-disposition"] == [
        "inline; filename*=utf-8''Se%C3%B1al%C3%A9tica.pdf"
    ]
    assert "X-Amz-Signature" in consulta
    # La respuesta que lleva la URL firmada no se guarda en cachés.
    assert "no-store" in respuesta["Cache-Control"]
    assert EventoAuditoria.objects.filter(accion=Accion.DOCUMENTO_VISTO).count() == 1

    descarga = parse_qs(urlsplit(portal.get(_portal(documento, "descargar"))["Location"]).query)
    assert descarga["response-content-disposition"][0].startswith("attachment;")
    assert EventoAuditoria.objects.filter(accion=Accion.DOCUMENTO_DESCARGADO).count() == 1


def test_con_s3_la_url_firmada_no_queda_en_los_logs_ni_en_la_auditoria(
    almacen_s3, cliente_a_activo, carpeta_a, administrador, caplog
):
    """SEG-10: quien lea los logs o la auditoría no obtiene un enlace de descarga."""
    documento = subir_documento(carpeta_a, administrador, archivos.pdf("Contrato.pdf"))
    portal = Client()
    entrar(portal, RUT_CLIENTE_A)
    # El nivel de producción: INFO en todos los registradores.
    with caplog.at_level(logging.INFO):
        respuesta = portal.get(_portal(documento, "descargar"))
    firma = parse_qs(urlsplit(respuesta["Location"]).query)["X-Amz-Signature"][0]

    assert len(firma) == 64
    assert firma not in caplog.text and "X-Amz-Signature" not in caplog.text
    for evento in EventoAuditoria.objects.all():
        assert firma not in evento.detalle and "X-Amz" not in evento.detalle
