"""Aislamiento entre empresas y papelera en las pantallas del portal: listar y buscar
(pruebas 2 y 4 de la sección 12.2; DOC-06, SEG-05).

Los endpoints de ver y descargar y las consultas están en documentos/tests/test_aislamiento.py.
"""

import datetime
import re
import uuid

import pytest
from django.core.management import call_command
from django.utils import timezone

from conftest import subir_documento
from documentos import services
from documentos.models import Documento
from documentos.tests import archivos
from empresas.models import Carpeta
from portal.tests.conftest import entregas, pagina

pytestmark = pytest.mark.django_db


def _ficha(documento):
    return f"/portal/documentos/{documento.pk}/"


def _carpeta(carpeta):
    return f"/portal/carpetas/{carpeta.pk}/"


@pytest.fixture
def de_a(administrador, carpeta_a):
    return subir_documento(carpeta_a, administrador, archivos.pdf("Matriz común de A.pdf"))


@pytest.fixture
def de_b(administrador, carpeta_b, cliente_b_activo):
    """Dos documentos de B: uno comparte una palabra del título con el de A."""
    return [
        subir_documento(carpeta_b, administrador, archivos.pdf("Protocolo reservado.pdf")),
        subir_documento(carpeta_b, administrador, archivos.pdf("Matriz común de B.pdf")),
    ]


def _datos_de_b(empresa_b, carpeta_b, de_b):
    """Todo lo que, de aparecer en una página de A, delataría a la empresa B."""
    return [
        empresa_b.razon_social,
        "76.222.222-1",
        "762222221",
        str(empresa_b.pk),
        carpeta_b.nombre,
        str(carpeta_b.pk),
        "Protocolo reservado",
        "Matriz común de B",
        *[str(documento.pk) for documento in de_b],
        *[str(documento.version_vigente_id) for documento in de_b],
    ]


def test_prueba_2_las_pantallas_de_a_no_listan_nada_de_b(
    portal_a, de_a, de_b, empresa_b, carpeta_a, carpeta_b, espia
):
    ajeno = _datos_de_b(empresa_b, carpeta_b, de_b)
    rutas = (
        "/portal/",
        "/portal/carpetas/",
        _carpeta(carpeta_a),
        _carpeta(carpeta_a) + "?orden=nombre",
        _ficha(de_a),
        "/portal/buscar/?q=matriz",
        "/cuenta/",
    )
    for ruta in rutas:
        respuesta = portal_a.get(ruta)
        contenido = respuesta.content.decode()
        assert respuesta.status_code == 200, ruta
        for dato in ajeno:
            assert dato not in contenido, (ruta, dato)
    # Los contadores cuentan solo lo de A: una carpeta con un documento.
    inicio = portal_a.get("/portal/").content.decode()
    assert re.findall(r"/portal/carpetas/[0-9a-f-]{36}/", inicio) == [_carpeta(carpeta_a)]
    assert re.findall(r"/portal/documentos/[0-9a-f-]{36}/", inicio) == [_ficha(de_a)]
    assert "1 documento ·" in inicio
    assert entregas() == 0 and espia == []


def test_prueba_2_la_carpeta_y_la_ficha_de_b_responden_404_como_si_no_existieran(
    portal_a, de_a, de_b, carpeta_b, espia
):
    carpeta_inexistente = portal_a.get(f"/portal/carpetas/{uuid.uuid4()}/")
    ficha_inexistente = portal_a.get(f"/portal/documentos/{uuid.uuid4()}/")
    assert carpeta_inexistente.status_code == 404 and ficha_inexistente.status_code == 404
    for ruta in (_carpeta(carpeta_b), _carpeta(carpeta_b) + "?orden=nombre&page=1"):
        respuesta = portal_a.get(ruta)
        assert respuesta.status_code == 404, ruta
        assert pagina(respuesta) == pagina(carpeta_inexistente)
    for documento in de_b:
        respuesta = portal_a.get(_ficha(documento))
        assert respuesta.status_code == 404
        # DOC-06: la misma respuesta que para un documento que no existe.
        assert pagina(respuesta) == pagina(ficha_inexistente)
    assert entregas() == 0 and espia == []


def test_prueba_2_la_busqueda_solo_encuentra_documentos_de_la_propia_empresa(
    portal_a, de_a, de_b, empresa_b, carpeta_b, espia
):
    ajeno = _datos_de_b(empresa_b, carpeta_b, de_b)
    # El título exacto de un documento de B: sin resultados.
    for texto in ("Protocolo reservado", "protocolo", "Matriz común de B", "reservado.pdf"):
        contenido = portal_a.get("/portal/buscar/", {"q": texto}).content.decode()
        assert "Sin resultados para" in contenido, texto
        assert "/descargar/" not in contenido and str(de_b[0].pk) not in contenido
    # Una palabra que comparten A y B: solo el de A.
    contenido = portal_a.get("/portal/buscar/", {"q": "matriz común"}).content.decode()
    assert "1 resultado para" in contenido and _ficha(de_a) in contenido
    for dato in ajeno:
        assert dato not in contenido, dato
    # Parámetros hechos a mano no amplían la búsqueda.
    for extra in (
        {"empresa": str(empresa_b.pk)},
        {"carpeta": str(carpeta_b.pk)},
        {"empresa_id": str(empresa_b.pk), "todas": "1"},
    ):
        contenido = portal_a.get("/portal/buscar/", {"q": "matriz", **extra}).content.decode()
        assert "1 resultado para" in contenido, extra
        for dato in ajeno:
            assert dato not in contenido, (extra, dato)
    assert entregas() == 0 and espia == []


def test_prueba_2_ninguna_pantalla_muestra_el_archivo_anterior_tras_un_reemplazo(
    portal_a, administrador, carpeta_a
):
    documento = subir_documento(carpeta_a, administrador, archivos.pdf("Borrador interno.pdf"))
    anterior = documento.version_vigente
    services.editar(
        documento, titulo="Reglamento", descripcion="", actor=administrador, request=None
    )
    services.reemplazar(
        documento, archivos.pdf("Definitivo.pdf", b"% v2"), actor=administrador, request=None
    )
    for ruta in ("/portal/", _carpeta(carpeta_a), _ficha(documento), "/portal/buscar/?q=regla"):
        contenido = portal_a.get(ruta).content.decode()
        assert "Reglamento" in contenido, ruta
        assert "Borrador" not in contenido and str(anterior.pk) not in contenido, ruta
    assert "Sin resultados" in portal_a.get("/portal/buscar/?q=borrador").content.decode()


def test_prueba_4_un_documento_en_la_papelera_desaparece_de_todas_las_pantallas(
    portal_a, cliente_http_admin, administrador_activo, empresa_a, carpeta_a, espia
):
    """Prueba 4 y escenario E5 sobre los listados, con el administrador actuando por el panel."""
    subir_documento(carpeta_a, administrador_activo, archivos.pdf("Queda visible.pdf"))
    eliminado = subir_documento(
        carpeta_a, administrador_activo, archivos.pdf("Plan de emergencia.pdf")
    )
    sola = Carpeta.objects.create(empresa=empresa_a, nombre="Solo eliminados", orden=2)
    huerfano = subir_documento(sola, administrador_activo, archivos.pdf("Único de su carpeta.pdf"))
    inexistente = portal_a.get(f"/portal/documentos/{uuid.uuid4()}/")
    listados = ("/portal/", _carpeta(carpeta_a), "/portal/buscar/?q=plan")

    for ruta in listados:
        assert "Plan de emergencia" in portal_a.get(ruta).content.decode(), ruta
    assert "2 documentos" in portal_a.get("/portal/carpetas/").content.decode()

    base = f"/panel/clientes/{empresa_a.pk}/documentos"
    for documento in (eliminado, huerfano):
        assert cliente_http_admin.post(f"{base}/{documento.pk}/eliminar/").status_code == 302

    for ruta in (*listados, "/portal/carpetas/", _carpeta(sola), "/portal/buscar/?q=carpeta"):
        contenido = portal_a.get(ruta).content.decode()
        for dato in ("Plan de emergencia", "Único de su carpeta", eliminado.pk, huerfano.pk):
            assert str(dato) not in contenido, (ruta, dato)
    assert "Sin resultados para «plan»" in portal_a.get(listados[2]).content.decode()
    for documento in (eliminado, huerfano):
        respuesta = portal_a.get(_ficha(documento))
        assert respuesta.status_code == 404
        assert pagina(respuesta) == pagina(inexistente)
    # El contador baja, y la carpeta que solo tenía un eliminado queda en cero y sin fecha.
    carpetas = portal_a.get("/portal/carpetas/").content.decode()
    assert "1 documento ·" in carpetas and "0 documentos<" in carpetas
    assert carpetas.count("Actualizado el") == 1
    assert "Esta carpeta aún no tiene documentos" in portal_a.get(_carpeta(sola)).content.decode()
    assert entregas() == 0 and espia == []

    # Al restaurarlo, vuelve a todos los listados y a su ficha.
    assert cliente_http_admin.post(f"{base}/{eliminado.pk}/restaurar/").status_code == 302
    for ruta in (*listados, _ficha(eliminado)):
        assert "Plan de emergencia" in portal_a.get(ruta).content.decode(), ruta
    assert "2 documentos" in portal_a.get("/portal/carpetas/").content.decode()


def test_prueba_4_si_todo_esta_en_la_papelera_el_inicio_queda_como_sin_documentos(
    portal_a, administrador, documento_a
):
    services.eliminar(documento_a, actor=administrador, request=None)
    contenido = portal_a.get("/portal/").content.decode()
    assert "Aún no hay documentos disponibles" in contenido
    assert "Documentos recientes" not in contenido and "informe" not in contenido


def test_prueba_4_tras_la_purga_el_documento_no_aparece_en_ningun_listado(
    portal_a, administrador, documento_a, carpeta_a
):
    queda = subir_documento(carpeta_a, administrador, archivos.pdf("Sigue publicado.pdf"))
    services.eliminar(documento_a, actor=administrador, request=None)
    hace_31_dias = timezone.now() - datetime.timedelta(days=31)
    Documento.objects.filter(pk=documento_a.pk).update(eliminado_en=hace_31_dias)
    call_command("purgar_papelera")
    assert list(Documento.objects.all()) == [queda]
    for ruta in ("/portal/", "/portal/carpetas/", _carpeta(carpeta_a), "/portal/buscar/?q=i"):
        contenido = portal_a.get(ruta).content.decode()
        assert "informe" not in contenido and str(documento_a.pk) not in contenido, ruta
    assert portal_a.get(_ficha(documento_a)).status_code == 404
