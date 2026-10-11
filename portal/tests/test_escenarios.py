"""Escenarios de aceptación E3, E4, E5 y E7 del lado del cliente (sección 12.3).

El administrador actúa por las vistas reales del panel y el cliente por las del portal.
"""

import re
from urllib.parse import urlsplit

import pytest
from django.core import mail
from django.test import Client

from auditoria.models import EventoAuditoria
from auditoria.services import Accion
from conftest import CLAVE, RUT_CLIENTE_A, entrar, subir_documento
from documentos.models import Documento
from documentos.tests import archivos
from portal.tests.conftest import cuerpo, entregas, hoy

pytestmark = pytest.mark.django_db

NUEVA = "tornillo-violeta-marea-88"


def _ficha(documento, accion=""):
    return f"/portal/documentos/{documento.pk}/" + (f"{accion}/" if accion else "")


def _carpeta(carpeta):
    return f"/portal/carpetas/{carpeta.pk}/"


def _panel(documento, accion=""):
    base = f"/panel/clientes/{documento.empresa_id}/documentos/{documento.pk}/"
    return base + (f"{accion}/" if accion else "")


def _recientes(cliente_http):
    contenido = cliente_http.get("/portal/").content.decode()
    return contenido[contenido.index("Documentos recientes") :]


def test_e3_el_cliente_ve_los_aceptados_como_nuevos_descarga_uno_y_queda_en_la_auditoria(
    portal_a, cliente_http_admin, cliente_a_activo, carpeta_a, empresa_a, avanzar_el_reloj
):
    assert "Aún no hay documentos disponibles" in portal_a.get("/portal/").content.decode()

    subida = cliente_http_admin.post(
        f"/panel/clientes/{empresa_a.pk}/carpetas/{carpeta_a.pk}/subir/",
        {
            "archivos": [
                archivos.pdf("Matriz de riesgos 2026.pdf"),
                archivos.archivo("instalador.pdf", archivos.BYTES_EXE),
                archivos.ooxml("xlsx", "Inspección de extintores.xlsx"),
            ]
        },
    ).content.decode()
    assert subida.count("Aceptado.") == 2 and subida.count("Rechazado.") == 1

    # El cliente los ve en "Documentos recientes" con la etiqueta "Nuevo"; el rechazado no existe.
    recientes = _recientes(portal_a)
    matriz = Documento.objects.get(titulo="Matriz de riesgos 2026")
    planilla = Documento.objects.get(titulo="Inspección de extintores")
    assert _ficha(matriz) in recientes and _ficha(planilla) in recientes
    assert recientes.count(">Nuevo<") == 2 and "instalador" not in recientes
    assert f"2 documentos · Actualizado el {hoy()}" in portal_a.get("/portal/").content.decode()
    assert "Sin resultados" in portal_a.get("/portal/buscar/?q=instalador").content.decode()

    # Abre la ficha, descarga, y la auditoría registra la descarga.
    ficha = portal_a.get(_ficha(matriz)).content.decode()
    assert _ficha(matriz, "descargar") in ficha and entregas() == 0
    descarga = portal_a.get(_ficha(matriz, "descargar"), REMOTE_ADDR="203.0.113.9")
    assert descarga.status_code == 200 and cuerpo(descarga) == archivos.BYTES_PDF
    assert descarga["Content-Disposition"].startswith("attachment;")
    evento = EventoAuditoria.objects.get(accion=Accion.DOCUMENTO_DESCARGADO)
    assert evento.actor == cliente_a_activo and evento.empresa == empresa_a
    assert evento.objeto_uuid == matriz.pk and evento.ip == "203.0.113.9"
    # Navegar por el portal no registra descargas: solo la que hizo.
    assert entregas() == 1

    avanzar_el_reloj(days=14)
    assert ">Nuevo<" not in _recientes(portal_a)


def test_e4_tras_el_reemplazo_el_cliente_ve_y_descarga_solo_la_version_nueva(
    portal_a, cliente_http_admin, administrador_activo, carpeta_a, avanzar_el_reloj
):
    documento = subir_documento(carpeta_a, administrador_activo, archivos.pdf("Reglamento.pdf"))
    otro = subir_documento(carpeta_a, administrador_activo, archivos.pdf("Más reciente.pdf"))
    assert _recientes(portal_a).index(_ficha(otro)) < _recientes(portal_a).index(_ficha(documento))
    anterior = documento.version_vigente
    antes = portal_a.get(_ficha(documento)).content.decode()
    assert f"PDF · {len(archivos.BYTES_PDF)}\xa0bytes" in antes

    nuevo = archivos.ooxml("docx", "Reglamento corregido.docx")
    bytes_nuevos = nuevo.read()
    nuevo.seek(0)
    respuesta = cliente_http_admin.post(_panel(documento, "reemplazar"), {"archivo": nuevo})
    assert respuesta.status_code == 302

    # La ficha muestra el archivo nuevo, con su tipo y tamaño, y vuelve a estar primero.
    ficha = portal_a.get(_ficha(documento)).content.decode()
    assert "DOCX ·" in ficha and "PDF ·" not in ficha and ">Nuevo<" in ficha
    assert _ficha(documento, "ver") not in ficha  # un Word no se ve en el navegador
    recientes = _recientes(portal_a)
    assert recientes.index(_ficha(documento)) < recientes.index(_ficha(otro))
    descarga = portal_a.get(_ficha(documento, "descargar"))
    assert cuerpo(descarga) == bytes_nuevos
    assert "corregido.docx" in descarga["Content-Disposition"]

    # El cliente no tiene cómo pedir la versión anterior.
    for ruta in ("/portal/", _carpeta(carpeta_a), _ficha(documento)):
        assert str(anterior.pk) not in portal_a.get(ruta).content.decode()
    for accion in ("ver", "descargar"):
        ruta = f"{_ficha(documento)}versiones/{anterior.pk}/{accion}/"
        assert portal_a.get(ruta).status_code == 404
    # Aun con un parámetro inventado, lo entregado es siempre la versión vigente.
    con_parametro = portal_a.get(f"{_ficha(documento, 'descargar')}?version={anterior.pk}")
    assert cuerpo(con_parametro) == bytes_nuevos
    # El administrador sí ve ambas en el historial.
    historial = cliente_http_admin.get(_panel(documento)).content.decode()
    assert "Versión 2" in historial and "Versión 1" in historial


def test_e5_el_cliente_deja_de_ver_el_documento_eliminado_y_vuelve_a_verlo_al_restaurarlo(
    portal_a, cliente_http_admin, administrador_activo, carpeta_a
):
    documento = subir_documento(
        carpeta_a, administrador_activo, archivos.pdf("Plan de emergencia.pdf")
    )
    paginas = ("/portal/", _carpeta(carpeta_a), "/portal/buscar/?q=emergencia", _ficha(documento))

    def visible():
        return ["Plan de emergencia" in portal_a.get(ruta).content.decode() for ruta in paginas]

    assert visible() == [True] * 4
    assert cliente_http_admin.post(_panel(documento, "eliminar")).status_code == 302
    assert visible() == [False] * 4
    assert portal_a.get(_ficha(documento)).status_code == 404
    assert portal_a.get(_ficha(documento, "descargar")).status_code == 404
    assert "Aún no hay documentos disponibles" in portal_a.get("/portal/").content.decode()

    assert cliente_http_admin.post(_panel(documento, "restaurar")).status_code == 302
    assert visible() == [True] * 4
    assert portal_a.get(_ficha(documento, "descargar")).status_code == 200
    assert entregas() == 1


def test_e7_restablecer_la_contrasena_cierra_la_sesion_del_portal_en_el_otro_dispositivo(
    portal_a, cliente_a_activo, documento_a, carpeta_a, espia
):
    """El cliente está en el portal en un dispositivo y restablece su contraseña en otro."""
    protegidas = (
        "/portal/",
        "/portal/carpetas/",
        _carpeta(carpeta_a),
        "/portal/buscar/?q=informe",
        _ficha(documento_a),
        _ficha(documento_a, "ver"),
        _ficha(documento_a, "descargar"),
        "/cuenta/",
    )
    for ruta in protegidas[:5]:
        assert portal_a.get(ruta).status_code == 200, ruta

    # En otro dispositivo pide la recuperación y usa el enlace que llega a su correo.
    otro = Client()
    assert otro.post("/recuperar/", {"rut": RUT_CLIENTE_A}).status_code == 302
    (mensaje,) = mail.outbox
    assert mensaje.to == ["cliente.a@ejemplo.test"]
    enlace = urlsplit(re.search(r"http://\S+/restablecer/\S+/", mensaje.body).group(0)).path
    assert otro.get(enlace).status_code == 200
    respuesta = otro.post(enlace, {"new_password1": NUEVA, "new_password2": NUEVA})
    assert respuesta["Location"] == "/portal/"
    assert "Hola, Empresa A de Prueba SpA" in otro.get("/portal/").content.decode()

    # La sesión anterior quedó cerrada: cada pantalla la manda al acceso y nada se entrega.
    for ruta in protegidas:
        respuesta = portal_a.get(ruta)
        assert respuesta.status_code == 302, ruta
        assert respuesta["Location"].startswith("/acceso/?next=/"), ruta
    assert entregas() == 0 and espia == []
    assert EventoAuditoria.objects.filter(accion=Accion.RESTABLECIMIENTO).count() == 1

    # La contraseña anterior ya no sirve; con la nueva vuelve a entrar y a descargar.
    assert entrar(portal_a, RUT_CLIENTE_A, CLAVE).status_code == 200
    assert entrar(portal_a, RUT_CLIENTE_A, NUEVA)["Location"] == "/portal/"
    assert portal_a.get(_ficha(documento_a, "descargar")).status_code == 200
    # El enlace no se puede volver a usar.
    assert Client().get(enlace).status_code == 404
