"""Plazo de conservación de las solicitudes: `depurar_solicitudes` (SEG-12)."""

import datetime
import io
import logging
import runpy

import pytest
from django.conf import settings as configuracion
from django.core.checks import run_checks
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import Accion
from solicitudes import services
from solicitudes.models import Solicitud

pytestmark = pytest.mark.django_db

NOMBRE = "Persona Que Consulta"
CORREO = "persona@ejemplo.test"
TELEFONO = "+56 9 5555 0000"
MENSAJE = "Mensaje con un dato que no debe salir de la solicitud."
NOTAS = "Nota interna sobre la persona."
DATOS_PERSONALES = (NOMBRE, "Persona", CORREO, TELEFONO, "5555", MENSAJE, NOTAS)


def _solicitud(dias, tipo=Solicitud.Tipo.CONSULTA, **campos):
    """Una solicitud recibida hace `dias` días (menos un minuto de margen si dias es 0)."""
    solicitud = Solicitud.objects.create(
        tipo=tipo,
        nombre=NOMBRE,
        email=CORREO,
        telefono=TELEFONO,
        mensaje=MENSAJE,
        consentimiento=True,
        consentimiento_en=timezone.now(),
        **campos,
    )
    Solicitud.objects.filter(pk=solicitud.pk).update(
        creado_en=timezone.now() - datetime.timedelta(days=dias)
    )
    return solicitud


def _depurar(*argumentos):
    salida = io.StringIO()
    call_command("depurar_solicitudes", *argumentos, stdout=salida)
    return salida.getvalue()


def _fecha_de_corte(dias=365):
    limite = timezone.localtime(timezone.now() - datetime.timedelta(days=dias))
    return limite.strftime("%d-%m-%Y")


def test_borra_solo_las_solicitudes_anteriores_al_plazo(administrador):
    reciente = _solicitud(0)
    casi = _solicitud(364, tipo=Solicitud.Tipo.COTIZACION)
    # Vencidas, en cualquier estado y con lo que lleven encima.
    _solicitud(366)
    _solicitud(400, estado=Solicitud.Estado.PENDIENTE, notas_internas=NOTAS)
    _solicitud(
        800,
        tipo=Solicitud.Tipo.COTIZACION,
        estado=Solicitud.Estado.RESUELTA,
        notificacion=Solicitud.Notificacion.FALLIDA,
        notificacion_error="El servidor de correo no respondió",
    )

    salida = _depurar()

    assert set(Solicitud.objects.values_list("pk", flat=True)) == {reciente.pk, casi.pk}
    assert salida.strip() == (
        f"Se borraron 3 solicitudes anteriores al {_fecha_de_corte()} "
        "(2 consultas, 1 cotizaciones)."
    )


def test_deja_un_evento_con_el_conteo_y_sin_datos_personales(administrador, caplog):
    vieja = _solicitud(500, notas_internas=NOTAS)
    # Un evento anterior de esa solicitud: se queda, con su UUID, hasta su propio plazo.
    services.cambiar_estado(vieja, Solicitud.Estado.RESUELTA, actor=administrador, request=None)
    _solicitud(500, tipo=Solicitud.Tipo.COTIZACION)

    with caplog.at_level(logging.INFO):
        salida = _depurar()

    evento = EventoAuditoria.objects.get(accion=Accion.SOLICITUDES_DEPURADAS)
    assert evento.detalle == (
        f"2 solicitudes anteriores al {_fecha_de_corte()} (1 consultas, 1 cotizaciones)"
    )
    assert evento.actor is None and evento.ip is None and evento.objeto_uuid is None
    anterior = EventoAuditoria.objects.get(accion=Accion.SOLICITUD_ESTADO)
    assert anterior.objeto_uuid == vieja.pk and not Solicitud.objects.filter(pk=vieja.pk).exists()
    # Ni la auditoría, ni la salida, ni el log llevan datos de las personas.
    textos = [salida, caplog.text, *EventoAuditoria.objects.values_list("detalle", flat=True)]
    for texto in textos:
        for dato in DATOS_PERSONALES:
            assert dato not in texto, dato


def test_sin_solicitudes_vencidas_no_hay_evento():
    _solicitud(10)
    assert "Se borraron 0 solicitudes" in _depurar()
    assert Solicitud.objects.count() == 1
    assert not EventoAuditoria.objects.filter(accion=Accion.SOLICITUDES_DEPURADAS).exists()


def test_simular_cuenta_y_no_borra_ni_registra(caplog):
    _solicitud(366)
    _solicitud(900, tipo=Solicitud.Tipo.COTIZACION)
    _solicitud(1)

    with caplog.at_level(logging.INFO):
        salida = _depurar("--simular")

    assert salida.strip() == (
        f"Simulación: se borrarían 2 solicitudes anteriores al {_fecha_de_corte()} "
        "(1 consultas, 1 cotizaciones). No se borró nada."
    )
    assert Solicitud.objects.count() == 3
    assert not EventoAuditoria.objects.exists() and caplog.text == ""


def test_el_plazo_sale_de_la_configuracion(settings):
    _solicitud(31)
    _solicitud(29)
    settings.SOLICITUDES_RETENCION_DIAS = 30
    assert f"Se borraron 1 solicitudes anteriores al {_fecha_de_corte(30)}" in _depurar()
    assert Solicitud.objects.count() == 1


def test_el_plazo_por_omision_es_de_365_dias():
    assert configuracion.SOLICITUDES_RETENCION_DIAS == 365


@pytest.mark.parametrize("dias", [29, 1, 0, -5])
def test_un_plazo_menor_que_30_dias_falla_sin_borrar_nada(settings, dias):
    _solicitud(400)
    settings.SOLICITUDES_RETENCION_DIAS = dias
    for argumentos in ((), ("--simular",)):
        with pytest.raises(CommandError) as error:
            _depurar(*argumentos)
        assert str(error.value) == (
            f"SOLICITUDES_RETENCION_DIAS vale {dias} y el mínimo es 30: con menos se borrarían "
            "solicitudes que todavía se están atendiendo. No se borró nada."
        )
    assert Solicitud.objects.count() == 1 and not EventoAuditoria.objects.exists()
    # El arranque también lo dice: `manage.py check` falla antes de servir.
    errores = [error for error in run_checks() if error.id == "solicitudes.E001"]
    assert len(errores) == 1 and f"vale {dias} y el mínimo es 30" in errores[0].msg


def test_un_plazo_de_30_dias_es_valido(settings):
    settings.SOLICITUDES_RETENCION_DIAS = 30
    assert not [error for error in run_checks() if error.id == "solicitudes.E001"]
    assert "Se borraron 0 solicitudes" in _depurar()


def test_la_consulta_liviana_cuenta_lo_mismo_que_la_tarea(settings, monkeypatch):
    """`docker/pendientes.py depurar_solicitudes` decide si vale la pena cargar la aplicación:
    si contara de menos, una solicitud vencida se quedaría sin borrar."""
    guion = runpy.run_path(str(settings.BASE_DIR / "docker" / "pendientes.py"))
    texto, consulta, parametros = guion["TAREAS"]["depurar_solicitudes"]

    def segun_el_guion():
        with connection.cursor() as cursor:
            cursor.execute(consulta, parametros())
            return cursor.fetchone()[0]

    def segun_la_tarea():
        return Solicitud.objects.vencidas(
            ahora=timezone.now(), dias=settings.SOLICITUDES_RETENCION_DIAS
        ).count()

    monkeypatch.delenv("SOLICITUDES_RETENCION_DIAS", raising=False)
    assert texto == "Solicitudes vencidas"
    assert segun_el_guion() == segun_la_tarea() == 0
    _solicitud(364)
    assert segun_el_guion() == segun_la_tarea() == 0
    _solicitud(366)
    _solicitud(700, tipo=Solicitud.Tipo.COTIZACION)
    assert segun_el_guion() == segun_la_tarea() == 2

    # El plazo sale de la misma variable de entorno que usa la aplicación.
    monkeypatch.setenv("SOLICITUDES_RETENCION_DIAS", "90")
    settings.SOLICITUDES_RETENCION_DIAS = 90
    assert segun_el_guion() == segun_la_tarea() == 3
    # La tarea de reintentos sigue siendo la que corre sin argumento.
    assert next(iter(guion["TAREAS"])) == "reintentar_notificaciones"
