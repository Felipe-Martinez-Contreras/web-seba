"""Listado de auditoría del panel (ADM-11) y retención (AUD-03)."""

import io
from datetime import UTC, datetime, timedelta

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from auditoria.management.commands.depurar_auditoria import restar_meses
from auditoria.models import EventoAuditoria
from auditoria.services import Accion, registrar

pytestmark = pytest.mark.django_db


def _con_fecha(evento, fecha):
    """Mueve la fecha de un evento por SQL: la aplicación no permite editarlo."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE auditoria_eventoauditoria SET fecha = %s WHERE id = %s", [fecha, evento.pk]
        )


@pytest.fixture
def eventos(cliente_a, cliente_b, administrador):
    antiguo = registrar(Accion.ACCESO_EXITOSO, actor=cliente_a, detalle="evento antiguo")
    _con_fecha(antiguo, timezone.now() - timedelta(days=40))
    return {
        "antiguo": antiguo,
        "de_a": registrar(Accion.CAMBIO_CONTRASENA, actor=cliente_a, detalle="evento de A"),
        "de_b": registrar(Accion.ACCESO_EXITOSO, actor=cliente_b, detalle="evento de B"),
        "fallido": registrar(
            Accion.ACCESO_FALLIDO, rut_intentado="9.876.543-3", detalle="evento fallido"
        ),
        "del_admin": registrar(
            Accion.DESBLOQUEO,
            actor=administrador,
            empresa=cliente_a.empresa,
            objeto=cliente_a,
            detalle="evento del administrador",
            ip="203.0.113.7",
        ),
    }


def _detalles(cliente_http, consulta=""):
    contenido = cliente_http.get("/panel/auditoria/" + consulta).content.decode()
    return {
        clave
        for clave in ("antiguo", "de A", "de B", "fallido", "del administrador")
        if f"evento {clave}" in contenido
    }


def test_el_listado_muestra_los_eventos_del_mas_nuevo_al_mas_antiguo(
    cliente_http_admin, eventos, cliente_a
):
    contenido = cliente_http_admin.get("/panel/auditoria/").content.decode()
    assert _detalles(cliente_http_admin) == {
        "antiguo",
        "de A",
        "de B",
        "fallido",
        "del administrador",
    }
    assert contenido.index("evento del administrador") < contenido.index("evento antiguo")
    # Cada fila identifica al actor, o el RUT que se intentó, y la IP.
    assert "Cliente de A" in contenido and "11.111.111-1" in contenido
    assert "RUT ingresado:" in contenido and "9.876.543-3" in contenido
    assert "203.0.113.7" in contenido and "Empresa A de Prueba SpA" in contenido
    assert "Desbloqueo manual" in contenido
    assert timezone.localtime(eventos["de_a"].fecha).strftime("%d-%m-%Y %H:%M") in contenido


def test_los_filtros_por_cliente_usuario_accion_y_fechas(
    cliente_http_admin, eventos, cliente_a, cliente_b
):
    empresa_a = cliente_a.empresa_id
    assert _detalles(cliente_http_admin, f"?empresa={empresa_a}") == {
        "antiguo",
        "de A",
        "del administrador",
    }
    assert _detalles(cliente_http_admin, "?rut=22.222.222-2") == {"de B"}
    # El RUT también encuentra los intentos fallidos de quien no tiene cuenta.
    assert _detalles(cliente_http_admin, "?rut=98765433") == {"fallido"}
    assert _detalles(cliente_http_admin, "?accion=acceso_exitoso") == {"antiguo", "de B"}
    hoy = timezone.localdate()
    assert "antiguo" not in _detalles(cliente_http_admin, f"?desde={hoy.isoformat()}")
    ayer = (hoy - timedelta(days=1)).isoformat()
    assert _detalles(cliente_http_admin, f"?hasta={ayer}") == {"antiguo"}
    combinado = f"?empresa={empresa_a}&accion=acceso_exitoso&hasta={ayer}"
    assert _detalles(cliente_http_admin, combinado) == {"antiguo"}

    vacio = cliente_http_admin.get("/panel/auditoria/?rut=1-9").content.decode()
    assert "Sin resultados" in vacio and "Quitar filtros" in vacio


@pytest.mark.parametrize(
    "consulta",
    [
        "?rut=11.111.111-2",
        "?desde=ayer",
        "?accion=inventada",
        "?empresa=00000000-0000-4000-8000-000000000000",
        "?desde=2026-02-01&hasta=2026-01-01",
    ],
)
def test_un_filtro_invalido_no_muestra_eventos_y_lo_explica(cliente_http_admin, eventos, consulta):
    contenido = cliente_http_admin.get("/panel/auditoria/" + consulta).content.decode()
    assert "Revise los filtros" in contenido and 'aria-invalid="true"' in contenido
    assert _detalles(cliente_http_admin, consulta) == set()


def test_el_listado_es_de_solo_lectura_y_pagina_sin_consultas_por_fila(
    cliente_http_admin, cliente_a, django_assert_max_num_queries
):
    EventoAuditoria.objects.bulk_create(
        EventoAuditoria(accion=Accion.ACCESO_EXITOSO, actor=cliente_a, empresa=cliente_a.empresa)
        for _ in range(30)
    )
    with django_assert_max_num_queries(12):
        contenido = cliente_http_admin.get("/panel/auditoria/").content.decode()
    assert contenido.count('data-etiqueta="Acción"') == 25 and "Página 1 de 2" in contenido
    segunda = cliente_http_admin.get("/panel/auditoria/?page=2&accion=acceso_exitoso")
    assert segunda.content.decode().count('data-etiqueta="Acción"') == 5
    # No hay nada que enviar: la página no acepta POST ni ofrece editar o borrar.
    assert cliente_http_admin.post("/panel/auditoria/").status_code == 405
    assert 'method="post"' not in contenido.split('id="contenido"')[1]
    assert EventoAuditoria.objects.count() == 30


def test_la_pestana_actividad_muestra_solo_los_eventos_de_ese_cliente(
    cliente_http_admin, eventos, cliente_a, cliente_b
):
    de_a = cliente_http_admin.get(
        f"/panel/clientes/{cliente_a.empresa_id}/actividad/"
    ).content.decode()
    assert "evento de A" in de_a and "evento del administrador" in de_a
    assert "evento de B" not in de_a and "evento fallido" not in de_a
    assert f"/panel/auditoria/?empresa={cliente_a.empresa_id}" in de_a
    de_b = cliente_http_admin.get(
        f"/panel/clientes/{cliente_b.empresa_id}/actividad/"
    ).content.decode()
    assert "evento de B" in de_b and "evento de A" not in de_b


def test_la_actividad_de_un_cliente_sin_eventos_lo_explica(cliente_http_admin, empresa_a):
    contenido = cliente_http_admin.get(f"/panel/clientes/{empresa_a.pk}/actividad/")
    assert "Aún no hay actividad registrada" in contenido.content.decode()


def _depurar():
    salida = io.StringIO()
    call_command("depurar_auditoria", stdout=salida)
    return salida.getvalue()


def test_depurar_auditoria_borra_solo_lo_anterior_a_la_retencion(eventos, settings):
    settings.AUDITORIA_RETENCION_MESES = 1
    salida = _depurar()
    assert "Se borraron 1 eventos anteriores al" in salida
    assert not EventoAuditoria.objects.filter(pk=eventos["antiguo"].pk).exists()
    assert EventoAuditoria.objects.filter(detalle__startswith="evento ").count() == 4
    # La depuración deja su propio rastro.
    rastro = EventoAuditoria.objects.get(accion=Accion.AUDITORIA_DEPURADA)
    assert rastro.detalle.startswith("1 eventos anteriores al ")

    # Sin nada que borrar no agrega eventos.
    assert "Se borraron 0 eventos" in _depurar()
    assert EventoAuditoria.objects.filter(accion=Accion.AUDITORIA_DEPURADA).count() == 1


def test_con_la_retencion_por_defecto_no_se_borra_lo_reciente(eventos, settings):
    assert settings.AUDITORIA_RETENCION_MESES == 24
    _depurar()
    assert EventoAuditoria.objects.count() == 5


def test_depurar_auditoria_rechaza_una_retencion_invalida(eventos, settings):
    settings.AUDITORIA_RETENCION_MESES = 0
    with pytest.raises(CommandError):
        _depurar()
    assert EventoAuditoria.objects.count() == 5


def test_restar_meses_respeta_el_largo_de_cada_mes():
    assert restar_meses(datetime(2026, 3, 31, 10, tzinfo=UTC), 1) == datetime(
        2026, 2, 28, 10, tzinfo=UTC
    )
    assert restar_meses(datetime(2026, 1, 15, tzinfo=UTC), 24) == datetime(2024, 1, 15, tzinfo=UTC)
    assert restar_meses(datetime(2026, 1, 15, tzinfo=UTC), 1) == datetime(2025, 12, 15, tzinfo=UTC)
