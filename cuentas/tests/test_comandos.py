"""Comandos de gestión: primer administrador y desbloqueo (AUT-12, AUT-04)."""

import io
import re

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client

from auditoria.models import EventoAuditoria
from auditoria.services import Accion
from conftest import CLAVE, RUT_CLIENTE_A, RUT_INEXISTENTE, entrar
from cuentas import bloqueo
from cuentas.models import EnlaceAcceso, Usuario

pytestmark = pytest.mark.django_db

NUEVA = "tornillo-violeta-marea-88"


def _ejecutar(*argumentos):
    salida = io.StringIO()
    call_command(*argumentos, stdout=salida)
    return salida.getvalue()


def test_crear_administrador_no_pide_contrasena_y_entrega_un_enlace_de_activacion(client):
    salida = _ejecutar(
        "crear_administrador",
        "--rut=12.345.678-5",
        "--nombre=Primera Administradora",
        "--email=admin@ejemplo.test",
    )
    usuario = Usuario.objects.get()
    assert usuario.rut == "123456785" and usuario.es_administrador
    assert usuario.empresa is None
    assert usuario.is_staff is False and usuario.is_superuser is False
    assert usuario.has_usable_password() is False
    assert EventoAuditoria.objects.get(accion=Accion.USUARIO_CREADO).objeto_uuid == usuario.uuid

    enlace = EnlaceAcceso.objects.get()
    assert enlace.tipo == EnlaceAcceso.Tipo.ACTIVACION
    url = re.search(r"http://testserver(/activar/\S+/)", salida).group(1)
    respuesta = client.post(url, {"new_password1": NUEVA, "new_password2": NUEVA})
    # Tras activar, lo primero es configurar el segundo factor.
    assert respuesta["Location"] == "/acceso/verificacion/?next=/panel/"
    assert client.get("/acceso/2fa/configurar/").status_code == 200


def test_crear_administrador_pregunta_lo_que_no_se_entrego(monkeypatch):
    respuestas = iter(["12.345.678-5", "Administradora", "admin@ejemplo.test"])
    monkeypatch.setattr("builtins.input", lambda pregunta: next(respuestas))
    _ejecutar("crear_administrador")
    assert Usuario.objects.get().email == "admin@ejemplo.test"


def test_crear_administrador_tecnico_puede_entrar_al_admin_de_django():
    _ejecutar(
        "crear_administrador",
        "--tecnico",
        "--rut=12.345.678-5",
        "--nombre=Soporte",
        "--email=soporte@ejemplo.test",
    )
    usuario = Usuario.objects.get()
    assert usuario.is_staff and usuario.is_superuser and usuario.es_administrador
    assert usuario.has_usable_password() is False


@pytest.mark.parametrize(
    ("argumentos", "mensaje"),
    [
        (["--rut=12.345.678-9", "--nombre=X", "--email=a@ejemplo.test"], "RUT válido"),
        (["--rut=12.345.678-5", "--nombre=X", "--email="], "obligatorio"),
        (["--rut=12.345.678-5", "--nombre=X", "--email=no-es-correo"], "correo"),
    ],
)
def test_crear_administrador_valida_los_datos(monkeypatch, argumentos, mensaje):
    monkeypatch.setattr("builtins.input", lambda pregunta: "")
    with pytest.raises(CommandError, match=mensaje):
        _ejecutar("crear_administrador", *argumentos)
    assert not Usuario.objects.exists()


def test_crear_administrador_rechaza_un_rut_repetido(administrador):
    with pytest.raises(CommandError, match="Ya existe"):
        _ejecutar(
            "crear_administrador", "--rut=12.345.678-5", "--nombre=Otra", "--email=o@ejemplo.test"
        )


def test_desbloquear_acceso_por_rut(cliente_a_activo, settings):
    settings.ACCESO_INTENTOS_MAXIMOS = 2
    visitante = Client()
    for _ in range(2):
        entrar(visitante, RUT_CLIENTE_A, "clave-equivocada-123")
    assert entrar(visitante, RUT_CLIENTE_A, CLAVE).status_code == 200

    assert "11.111.111-1" in _ejecutar("desbloquear_acceso", "--rut=11111111-1")
    assert entrar(visitante, RUT_CLIENTE_A, CLAVE).status_code == 302
    evento = EventoAuditoria.objects.get(accion=Accion.DESBLOQUEO)
    assert evento.objeto_uuid == cliente_a_activo.uuid and evento.actor is None


def test_desbloquear_acceso_de_un_rut_sin_cuenta_y_de_una_ip(settings):
    settings.ACCESO_INTENTOS_MAXIMOS = 2
    settings.ACCESO_INTENTOS_MAXIMOS_IP = 4
    for _ in range(2):
        bloqueo.registrar_fallo("98765433", "203.0.113.7")
    for _ in range(2):
        bloqueo.registrar_fallo("", "203.0.113.7")
    assert bloqueo.esta_bloqueado("", "203.0.113.7")

    _ejecutar("desbloquear_acceso", f"--rut={RUT_INEXISTENTE}")
    assert bloqueo.rut_bloqueado("98765433") is False
    _ejecutar("desbloquear_acceso", "--ip=203.0.113.7")
    assert bloqueo.esta_bloqueado("98765433", "203.0.113.7") is False
    assert EventoAuditoria.objects.filter(accion=Accion.DESBLOQUEO).count() == 2


def test_desbloquear_acceso_valida_sus_argumentos():
    with pytest.raises(CommandError, match="RUT"):
        _ejecutar("desbloquear_acceso", "--rut=11.111.111-2")
    with pytest.raises(CommandError, match="IP"):
        _ejecutar("desbloquear_acceso", "--ip=no-es-una-ip")
    with pytest.raises(CommandError):
        _ejecutar("desbloquear_acceso")
