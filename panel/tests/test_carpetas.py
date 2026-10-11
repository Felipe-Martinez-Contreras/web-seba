"""Carpetas de un cliente en el panel (ADM-07) y sus consultas por empresa (SEG-04)."""

import pytest
from django.db import IntegrityError, transaction

from auditoria.models import EventoAuditoria
from auditoria.services import Accion
from empresas import services
from empresas.models import Carpeta, Empresa

pytestmark = pytest.mark.django_db


def _documentos(empresa):
    return f"/panel/clientes/{empresa.pk}/documentos/"


def _de(carpeta, accion):
    return f"/panel/clientes/{carpeta.empresa_id}/carpetas/{carpeta.pk}/{accion}/"


def _nombres(empresa):
    return list(empresa.carpetas.values_list("nombre", flat=True))


def test_crear_una_carpeta_la_deja_al_final_y_queda_en_la_auditoria(
    cliente_http_admin, administrador_activo, carpeta_a, empresa_a
):
    url = f"/panel/clientes/{empresa_a.pk}/carpetas/nueva/"
    assert cliente_http_admin.get(url).status_code == 200
    respuesta = cliente_http_admin.post(
        url, {"nombre": "  Actas   del comité ", "descripcion": "Reuniones mensuales"}, follow=True
    )
    assert respuesta.redirect_chain == [(_documentos(empresa_a), 302)]
    contenido = respuesta.content.decode()
    assert "Se creó la carpeta Actas del comité." in contenido
    assert "Reuniones mensuales" in contenido
    assert _nombres(empresa_a) == ["Carpeta de A", "Actas del comité"]
    nueva = empresa_a.carpetas.get(nombre="Actas del comité")
    assert nueva.orden == 2
    evento = EventoAuditoria.objects.get(accion=Accion.CARPETA_CREADA)
    assert evento.actor == administrador_activo and evento.empresa == empresa_a
    assert evento.objeto_tipo == "carpeta" and evento.objeto_uuid == nueva.pk


def test_el_nombre_es_unico_dentro_de_la_empresa_sin_distinguir_mayusculas(
    cliente_http_admin, carpeta_a, empresa_a, empresa_b
):
    url = f"/panel/clientes/{empresa_a.pk}/carpetas/nueva/"
    respuesta = cliente_http_admin.post(url, {"nombre": "carpeta DE a", "descripcion": ""})
    assert respuesta.status_code == 200
    assert "Ya existe una carpeta con ese nombre en este cliente." in respuesta.content.decode()
    assert empresa_a.carpetas.count() == 1
    # En otra empresa el mismo nombre sí se puede usar.
    otra = f"/panel/clientes/{empresa_b.pk}/carpetas/nueva/"
    assert cliente_http_admin.post(otra, {"nombre": "Carpeta de A"}).status_code == 302
    # La base lo impide aunque se salte el formulario.
    with pytest.raises(IntegrityError), transaction.atomic():
        Carpeta.objects.create(empresa=empresa_a, nombre="CARPETA DE A")


def test_editar_renombra_y_permite_conservar_el_propio_nombre(
    cliente_http_admin, carpeta_a, empresa_a
):
    url = _de(carpeta_a, "editar")
    assert 'value="Carpeta de A"' in cliente_http_admin.get(url).content.decode()
    respuesta = cliente_http_admin.post(url, {"nombre": "Carpeta de A", "descripcion": "Nueva"})
    assert respuesta["Location"] == _documentos(empresa_a)
    cliente_http_admin.post(url, {"nombre": "Renombrada", "descripcion": "Nueva"})
    carpeta_a.refresh_from_db()
    assert (carpeta_a.nombre, carpeta_a.descripcion) == ("Renombrada", "Nueva")
    detalles = list(
        EventoAuditoria.objects.filter(accion=Accion.CARPETA_EDITADA)
        .order_by("id")
        .values_list("detalle", flat=True)
    )
    assert detalles == ["Carpeta de A", "Carpeta de A → Renombrada"]
    # Sin cambios no hay evento nuevo.
    cliente_http_admin.post(url, {"nombre": "Renombrada", "descripcion": "Nueva"})
    assert EventoAuditoria.objects.filter(accion=Accion.CARPETA_EDITADA).count() == 2


def test_ordenar_sube_y_baja_de_a_un_lugar(cliente_http_admin, empresa_a, empresa_b, carpeta_b):
    for orden, nombre in enumerate(["Uno", "Dos", "Tres"], start=1):
        Carpeta.objects.create(empresa=empresa_a, nombre=nombre, orden=orden)
    tres = empresa_a.carpetas.get(nombre="Tres")
    uno = empresa_a.carpetas.get(nombre="Uno")
    assert cliente_http_admin.get(_de(tres, "mover")).status_code == 405

    respuesta = cliente_http_admin.post(_de(tres, "mover"), {"direccion": "subir"})
    assert respuesta["Location"] == _documentos(empresa_a)
    assert _nombres(empresa_a) == ["Uno", "Tres", "Dos"]
    cliente_http_admin.post(_de(uno, "mover"), {"direccion": "bajar"})
    assert _nombres(empresa_a) == ["Tres", "Uno", "Dos"]
    # En los extremos, o con una dirección desconocida, no pasa nada.
    cliente_http_admin.post(_de(tres, "mover"), {"direccion": "subir"})
    cliente_http_admin.post(_de(uno, "mover"), {"direccion": "al-fondo"})
    assert _nombres(empresa_a) == ["Tres", "Uno", "Dos"]
    assert list(empresa_a.carpetas.values_list("orden", flat=True)) == [1, 2, 3]
    # Las carpetas de otra empresa no se tocan.
    carpeta_b.refresh_from_db()
    assert carpeta_b.orden == 1

    # La primera no ofrece subir ni la última bajar.
    contenido = cliente_http_admin.get(_documentos(empresa_a)).content.decode()
    assert 'aria-label="Subir Tres" disabled' in contenido
    assert 'aria-label="Bajar Dos" disabled' in contenido
    assert 'aria-label="Bajar Tres">' in contenido


def test_mover_ordena_tambien_carpetas_con_el_mismo_orden(empresa_a):
    for nombre in ("B", "A", "C"):
        Carpeta.objects.create(empresa=empresa_a, nombre=nombre, orden=0)
    assert _nombres(empresa_a) == ["A", "B", "C"]
    assert services.mover_carpeta(empresa_a.carpetas.get(nombre="C"), services.SUBIR) is True
    assert list(empresa_a.carpetas.values_list("nombre", "orden")) == [("A", 1), ("C", 2), ("B", 3)]
    assert services.mover_carpeta(empresa_a.carpetas.get(nombre="A"), services.SUBIR) is False


def test_eliminar_pide_confirmacion_borra_la_carpeta_y_queda_en_la_auditoria(
    cliente_http_admin, administrador_activo, carpeta_a, empresa_a
):
    url = _de(carpeta_a, "eliminar")
    pagina = cliente_http_admin.get(_documentos(empresa_a)).content.decode()
    dialogo = f"dialogo-eliminar-{carpeta_a.pk.hex}"
    assert f'data-abre-dialogo="{dialogo}"' in pagina and f'id="{dialogo}"' in pagina
    assert f'<form method="post" action="{url}">' in pagina
    assert cliente_http_admin.get(url).status_code == 405
    assert Carpeta.objects.filter(pk=carpeta_a.pk).exists()

    respuesta = cliente_http_admin.post(url, follow=True)
    contenido = respuesta.content.decode()
    assert "Se eliminó la carpeta Carpeta de A." in contenido
    assert "Este cliente aún no tiene carpetas" in contenido
    assert not Carpeta.objects.filter(pk=carpeta_a.pk).exists()
    evento = EventoAuditoria.objects.get(accion=Accion.CARPETA_ELIMINADA)
    assert evento.actor == administrador_activo and evento.empresa == empresa_a
    assert evento.objeto_uuid == carpeta_a.pk and evento.detalle == "Carpeta de A"
    assert cliente_http_admin.post(url).status_code == 404


@pytest.mark.parametrize("accion", ["editar", "mover", "eliminar"])
def test_una_carpeta_solo_se_alcanza_bajo_su_propia_empresa(
    cliente_http_admin, carpeta_a, empresa_b, accion
):
    url = f"/panel/clientes/{empresa_b.pk}/carpetas/{carpeta_a.pk}/{accion}/"
    respuesta = cliente_http_admin.post(url, {"nombre": "Tomada", "direccion": "subir"})
    assert respuesta.status_code == 404
    carpeta_a.refresh_from_db()
    assert carpeta_a.nombre == "Carpeta de A"
    assert not EventoAuditoria.objects.exists()


def test_visibles_para_acota_las_carpetas_a_la_empresa_del_cliente(
    carpeta_a, carpeta_b, cliente_a, cliente_b, administrador
):
    assert list(Carpeta.objects.visibles_para(cliente_a)) == [carpeta_a]
    assert list(Carpeta.objects.visibles_para(cliente_b)) == [carpeta_b]
    assert set(Carpeta.objects.visibles_para(administrador)) == {carpeta_a, carpeta_b}
    # El UUID correcto de una carpeta ajena no la hace visible.
    assert not Carpeta.objects.visibles_para(cliente_a).filter(pk=carpeta_b.pk).exists()


def test_buscar_empresas_ignora_el_formato_del_rut_y_el_texto_vacio(empresa_a, empresa_b):
    assert set(Empresa.objects.buscar("")) == {empresa_a, empresa_b}
    assert set(Empresa.objects.buscar("   ")) == {empresa_a, empresa_b}
    assert list(Empresa.objects.buscar("76.111.111-6")) == [empresa_a]
    assert list(Empresa.objects.buscar("76222")) == [empresa_b]
    assert list(Empresa.objects.buscar("ltda")) == [empresa_b]
    assert list(Empresa.objects.buscar("no existe")) == []


def test_una_empresa_con_carpetas_no_se_puede_borrar(carpeta_a, empresa_a):
    from django.db.models import ProtectedError

    with pytest.raises(ProtectedError):
        empresa_a.delete()
