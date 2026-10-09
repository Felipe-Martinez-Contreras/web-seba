"""Datos de prueba compartidos: dos empresas (A y B), un cliente por empresa y un administrador."""

import time

import pytest
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from cuentas.models import Usuario
from empresas.models import Empresa

CLAVE = "caballo-bateria-grapa-2026"
RUT_CLIENTE_A = "11.111.111-1"
RUT_CLIENTE_B = "22.222.222-2"
RUT_ADMINISTRADOR = "12.345.678-5"
RUT_INEXISTENTE = "9.876.543-3"


@pytest.fixture
def empresa_a(db):
    return Empresa.objects.create(rut="76.111.111-6", razon_social="Empresa A de Prueba SpA")


@pytest.fixture
def empresa_b(db):
    return Empresa.objects.create(rut="76.222.222-1", razon_social="Empresa B de Prueba Ltda.")


@pytest.fixture
def cliente_a(empresa_a):
    return Usuario.objects.create_user(
        RUT_CLIENTE_A, nombre="Cliente de A", rol=Usuario.Rol.CLIENTE, empresa=empresa_a
    )


@pytest.fixture
def cliente_b(empresa_b):
    return Usuario.objects.create_user(
        RUT_CLIENTE_B, nombre="Cliente de B", rol=Usuario.Rol.CLIENTE, empresa=empresa_b
    )


@pytest.fixture
def administrador(db):
    return Usuario.objects.create_user(
        RUT_ADMINISTRADOR,
        nombre="Administradora de Prueba",
        email="admin@ejemplo.test",
        rol=Usuario.Rol.ADMINISTRADOR,
    )


def _con_clave(usuario):
    usuario.set_password(CLAVE)
    usuario.save()
    return usuario


@pytest.fixture
def cliente_a_activo(cliente_a):
    """Cliente de A con la contraseña CLAVE y correo registrado."""
    cliente_a.email = "cliente.a@ejemplo.test"
    return _con_clave(cliente_a)


@pytest.fixture
def cliente_b_activo(cliente_b):
    return _con_clave(cliente_b)


@pytest.fixture
def administrador_activo(administrador):
    """Administrador con la contraseña CLAVE y sin 2FA configurado."""
    return _con_clave(administrador)


@pytest.fixture
def totp(administrador_activo):
    """Dispositivo TOTP confirmado del administrador."""
    return TOTPDevice.objects.create(
        user=administrador_activo, name="Aplicación de autenticación", confirmed=True
    )


@pytest.fixture
def codigos_de_recuperacion(administrador_activo):
    dispositivo = StaticDevice.objects.create(
        user=administrador_activo, name="Códigos de recuperación"
    )
    codigos = ["aaaa1111", "bbbb2222"]
    StaticToken.objects.bulk_create(StaticToken(device=dispositivo, token=c) for c in codigos)
    return codigos


def codigo_totp(dispositivo, pasos=0):
    """El código que mostraría la aplicación ahora, o `pasos` intervalos más adelante."""
    generador = TOTP(
        dispositivo.bin_key, dispositivo.step, dispositivo.t0, dispositivo.digits, dispositivo.drift
    )
    generador.time = time.time() + pasos * dispositivo.step
    return f"{generador.token():0{dispositivo.digits}d}"


def entrar(cliente_http, rut, clave=CLAVE, **extra):
    """Envía el formulario de acceso."""
    return cliente_http.post("/acceso/", {"rut": rut, "contrasena": clave}, **extra)


@pytest.fixture
def cliente_http_admin(client, administrador_activo, totp):
    """Cliente HTTP con la sesión de un administrador que ya pasó el segundo factor."""
    client.force_login(administrador_activo)
    sesion = client.session
    sesion[DEVICE_ID_SESSION_KEY] = totp.persistent_id
    sesion.save()
    return client
