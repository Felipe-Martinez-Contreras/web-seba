"""Aislamiento entre empresas y papelera (pruebas 2 y 4 de la sección 12.2; DOC-06, SEG-05).

Aquí se prueban las consultas y los endpoints de ver y descargar. Listar y buscar en las
pantallas del portal se prueba en portal/tests/test_aislamiento.py.
"""

import datetime
import re
import uuid

import pytest
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import Accion
from conftest import RUT_CLIENTE_A, RUT_CLIENTE_B, entrar
from documentos import almacenamiento, services
from documentos.models import Documento, VersionDocumento
from documentos.tests import archivos
from empresas.models import Carpeta

pytestmark = pytest.mark.django_db

ENTREGAS = (Accion.DOCUMENTO_VISTO, Accion.DOCUMENTO_DESCARGADO)


@pytest.fixture
def portal_a(cliente_a_activo):
    cliente = Client()
    entrar(cliente, RUT_CLIENTE_A)
    return cliente


@pytest.fixture
def espia(monkeypatch):
    """Registra cada intento de leer del almacenamiento para entregar un archivo."""
    llamadas = []
    original = almacenamiento.entregar

    def entregar(clave, **opciones):
        llamadas.append(clave)
        return original(clave, **opciones)

    monkeypatch.setattr(almacenamiento, "entregar", entregar)
    return llamadas


def _rutas(documento):
    return [f"/portal/documentos/{documento.pk}/{accion}/" for accion in ("ver", "descargar")]


def _pagina(respuesta):
    """El cuerpo sin el token CSRF, que cambia en cada respuesta."""
    return re.sub(rb'"X-CSRFToken": "[^"]+"', b"", respuesta.content)


def _entregas():
    return EventoAuditoria.objects.filter(accion__in=ENTREGAS).count()


def test_prueba_2_un_cliente_de_a_no_ve_ni_descarga_documentos_de_b_con_el_uuid_correcto(
    portal_a, cliente_b_activo, documento_a, documento_b, espia
):
    inexistente = portal_a.get(f"/portal/documentos/{uuid.uuid4()}/descargar/")
    assert inexistente.status_code == 404
    for ruta in _rutas(documento_b):
        respuesta = portal_a.get(ruta)
        assert respuesta.status_code == 404, ruta
        # DOC-06: la misma respuesta que para un documento que no existe.
        assert _pagina(respuesta) == _pagina(inexistente)
    # No se registró ninguna descarga ni se tocó el almacenamiento.
    assert _entregas() == 0 and espia == []

    # El documento sí existe y su dueño lo descarga: el 404 era por la empresa.
    portal_b = Client()
    entrar(portal_b, RUT_CLIENTE_B)
    assert portal_b.get(_rutas(documento_b)[1]).status_code == 200
    assert portal_a.get(_rutas(documento_a)[1]).status_code == 200
    assert espia == [documento_b.version_vigente.clave, documento_a.version_vigente.clave]
    assert _entregas() == 2
    assert all(
        evento.actor.empresa_id == evento.empresa_id
        for evento in EventoAuditoria.objects.filter(accion__in=ENTREGAS)
    )


def test_prueba_2_las_consultas_centralizadas_acotan_por_empresa(
    cliente_a, cliente_b, administrador, documento_a, documento_b, carpeta_b
):
    assert list(Documento.objects.visibles_para(cliente_a)) == [documento_a]
    assert list(Documento.objects.visibles_para(cliente_b)) == [documento_b]
    assert set(Documento.objects.visibles_para(administrador)) == {documento_a, documento_b}
    # Ni filtrando por el UUID exacto, ni por la carpeta, ni buscando por título.
    ajenos = Documento.objects.visibles_para(cliente_a)
    assert not ajenos.filter(pk=documento_b.pk).exists()
    assert not ajenos.filter(carpeta=carpeta_b).exists()
    assert not ajenos.filter(titulo__icontains=documento_b.titulo).exclude(pk=documento_a.pk)
    assert not Carpeta.objects.visibles_para(cliente_a).filter(pk=carpeta_b.pk).exists()

    versiones = VersionDocumento.objects.visibles_para(cliente_a)
    assert list(versiones) == [documento_a.version_vigente]
    assert not versiones.filter(pk=documento_b.version_vigente_id).exists()
    assert VersionDocumento.objects.visibles_para(administrador).count() == 2


def test_prueba_2_un_cliente_no_ve_versiones_anteriores_ni_de_su_propia_empresa(
    portal_a, cliente_a, administrador, documento_a, cliente_http_admin, administrador_activo
):
    anterior = documento_a.version_vigente
    nueva = services.reemplazar(
        documento_a, archivos.pdf("v2.pdf", b"% v2"), actor=administrador, request=None
    )
    assert list(VersionDocumento.objects.visibles_para(cliente_a)) == [nueva]
    assert not VersionDocumento.objects.visibles_para(cliente_a).filter(pk=anterior.pk).exists()
    # El portal no tiene ninguna ruta que reciba un UUID de versión.
    for accion in ("ver", "descargar"):
        ruta = f"/portal/documentos/{documento_a.pk}/versiones/{anterior.pk}/{accion}/"
        assert portal_a.get(ruta).status_code == 404
        # Y la del panel, que sí existe, le responde 404 por su rol.
        ruta = (
            f"/panel/clientes/{documento_a.empresa_id}/documentos/{documento_a.pk}"
            f"/versiones/{anterior.pk}/{accion}/"
        )
        assert portal_a.get(ruta).status_code == 404
    assert _entregas() == 0


def test_un_usuario_sin_rol_de_negocio_no_ve_nada(documento_a, cliente_a):
    cliente_a.rol = "otro"
    assert not Documento.objects.visibles_para(cliente_a).exists()
    assert not VersionDocumento.objects.visibles_para(cliente_a).exists()


def test_prueba_4_un_documento_en_la_papelera_no_es_accesible_para_el_cliente(
    portal_a, cliente_a, cliente_http_admin, administrador_activo, documento_a, espia
):
    """Prueba 4 y escenario E5, a nivel de endpoint."""
    assert portal_a.get(_rutas(documento_a)[1]).status_code == 200
    eliminar = f"/panel/clientes/{documento_a.empresa_id}/documentos/{documento_a.pk}/eliminar/"
    assert cliente_http_admin.post(eliminar).status_code == 302
    documento_a.refresh_from_db()
    assert documento_a.en_papelera and documento_a.eliminado_por == administrador_activo

    for ruta in _rutas(documento_a):
        assert portal_a.get(ruta).status_code == 404, ruta
    assert not Documento.objects.visibles_para(cliente_a).exists()
    assert not VersionDocumento.objects.visibles_para(cliente_a).exists()
    assert _entregas() == 1 and len(espia) == 1  # solo la descarga previa a eliminarlo

    # Decisión C: en la papelera tampoco lo descarga el administrador.
    panel = (
        f"/panel/clientes/{documento_a.empresa_id}/documentos/{documento_a.pk}"
        f"/versiones/{documento_a.version_vigente_id}/descargar/"
    )
    assert cliente_http_admin.get(panel).status_code == 404
    assert _entregas() == 1

    # Al restaurarlo, el cliente vuelve a verlo.
    restaurar = f"/panel/clientes/{documento_a.empresa_id}/documentos/{documento_a.pk}/restaurar/"
    assert cliente_http_admin.post(restaurar).status_code == 302
    assert portal_a.get(_rutas(documento_a)[1]).status_code == 200
    assert list(Documento.objects.visibles_para(cliente_a)) == [documento_a]


def test_prueba_4_tras_la_purga_no_quedan_ni_las_filas_ni_los_archivos(
    portal_a, administrador, documento_a, carpeta_a, almacen_de_prueba
):
    from conftest import subir_documento

    reciente = subir_documento(carpeta_a, administrador, archivos.pdf("reciente.pdf"))
    services.reemplazar(
        documento_a, archivos.pdf("v2.pdf", b"% v2"), actor=administrador, request=None
    )
    services.eliminar(documento_a, actor=administrador, request=None)
    services.eliminar(reciente, actor=administrador, request=None)
    hace_31_dias = timezone.now() - datetime.timedelta(days=31)
    Documento.objects.filter(pk=documento_a.pk).update(eliminado_en=hace_31_dias)
    assert len(almacen_de_prueba.claves()) == 3

    call_command("purgar_papelera")

    assert list(Documento.objects.all()) == [reciente]  # con menos de 30 días, sigue
    assert list(VersionDocumento.objects.all()) == [reciente.version_vigente]
    assert almacen_de_prueba.claves() == [reciente.version_vigente.clave]
    for ruta in _rutas(documento_a):
        assert portal_a.get(ruta).status_code == 404
