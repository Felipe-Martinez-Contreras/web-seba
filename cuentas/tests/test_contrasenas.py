"""Reglas de la contraseña (AUT-05, DEC-207): 10 caracteres, sin contraseñas comunes ni solo
números, y sin la regla de similitud con los datos del usuario."""

import io
import re

import pytest
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management import call_command

from conftest import CLAVE, RUT_CLIENTE_A, entrar
from cuentas import services
from cuentas.forms import reglas_contrasena
from cuentas.models import EnlaceAcceso

pytestmark = pytest.mark.django_db

ACTIVACION = EnlaceAcceso.Tipo.ACTIVACION
RESTABLECIMIENTO = EnlaceAcceso.Tipo.RESTABLECIMIENTO
REGLAS = (
    "Use al menos 10 caracteres. Puede ser una frase; no use solo números ni una "
    "contraseña muy conocida."
)


def _activar(cliente_http, usuario, clave):
    _, token = services.generar_enlace(usuario, ACTIVACION)
    return cliente_http.post(f"/activar/{token}/", {"new_password1": clave, "new_password2": clave})


def test_los_validadores_son_largo_comunes_y_solo_numeros():
    nombres = [
        validador["NAME"].rsplit(".", 1)[1] for validador in settings.AUTH_PASSWORD_VALIDATORS
    ]
    assert nombres == [
        "MinimumLengthValidator",
        "CommonPasswordValidator",
        "NumericPasswordValidator",
    ]
    assert settings.AUTH_PASSWORD_VALIDATORS[0]["OPTIONS"] == {"min_length": 10}


def test_nueve_caracteres_fallan_y_diez_pasan(client, cliente_a):
    respuesta = _activar(client, cliente_a, "caballo-1")
    assert respuesta.status_code == 200
    assert "por lo menos 10 caracteres" in respuesta.content.decode()
    cliente_a.refresh_from_db()
    assert not cliente_a.has_usable_password()

    respuesta = _activar(client, cliente_a, "caballo-12")
    assert respuesta.status_code == 302
    cliente_a.refresh_from_db()
    assert cliente_a.check_password("caballo-12")


@pytest.mark.parametrize(
    "parecida", ["cliente.a@ejemplo.test", "Cliente de A 2026", "111111111-clave"]
)
def test_una_contrasena_parecida_a_los_datos_del_usuario_ahora_pasa(cliente_a, parecida):
    """Nombre «Cliente de A», correo cliente.a@ejemplo.test y RUT 11.111.111-1."""
    cliente_a.email = "cliente.a@ejemplo.test"
    validate_password(parecida, user=cliente_a)


def test_una_contrasena_parecida_al_nombre_se_acepta_en_mi_cuenta(client, cliente_a_activo):
    entrar(client, RUT_CLIENTE_A)
    respuesta = client.post(
        "/cuenta/",
        {
            "old_password": CLAVE,
            "new_password1": "Cliente de A 2026",
            "new_password2": "Cliente de A 2026",
        },
    )
    assert respuesta.status_code == 302
    cliente_a_activo.refresh_from_db()
    assert cliente_a_activo.check_password("Cliente de A 2026")


@pytest.mark.parametrize(
    ("debil", "mensaje"),
    [
        ("123456789", "numérica"),
        ("1234567890", "numérica"),
        ("1q2w3e4r5t6y7u8i", "demasiado común"),
        ("password123", "demasiado común"),
    ],
)
def test_solo_numeros_y_las_comunes_siguen_fallando(client, cliente_a, debil, mensaje):
    respuesta = _activar(client, cliente_a, debil)
    assert respuesta.status_code == 200
    assert mensaje in respuesta.content.decode(), debil
    cliente_a.refresh_from_db()
    assert not cliente_a.has_usable_password()


def test_una_contrasena_anterior_que_ya_no_cumple_sigue_sirviendo(client, cliente_a):
    """Las reglas valen al crear o cambiar una contraseña, no al entrar: nadie debe cambiarla."""
    cliente_a.set_password("corta-1")
    cliente_a.save()
    respuesta = entrar(client, RUT_CLIENTE_A, "corta-1")
    assert respuesta.status_code == 302 and respuesta["Location"] == "/portal/"


def _antes_del_campo(contenido, nombre="new_password1"):
    reglas = contenido.index('id="reglas-contrasena"')
    campo = re.search(rf'<input[^>]+name="{nombre}"[^>]*>', contenido)
    assert reglas < campo.start()
    assert 'aria-describedby="reglas-contrasena"' in campo.group(0)
    assert REGLAS in contenido
    # Ya no se repite debajo como ayuda del campo.
    assert "new_password1_helptext" not in contenido


@pytest.mark.parametrize("tipo", [ACTIVACION, RESTABLECIMIENTO])
def test_las_reglas_se_ven_antes_de_escribir_en_los_enlaces(client, cliente_a_activo, tipo):
    _, token = services.generar_enlace(cliente_a_activo, tipo)
    ruta = "activar" if tipo == ACTIVACION else "restablecer"
    _antes_del_campo(client.get(f"/{ruta}/{token}/").content.decode())


def test_las_reglas_se_ven_antes_de_escribir_en_mi_cuenta(client, cliente_a_activo):
    entrar(client, RUT_CLIENTE_A)
    contenido = client.get("/cuenta/").content.decode()
    _antes_del_campo(contenido)
    # Después de la contraseña actual y antes de la nueva.
    assert contenido.index('name="old_password"') < contenido.index('id="reglas-contrasena"')


def test_las_reglas_se_ven_tambien_cuando_hay_un_error(client, cliente_a):
    respuesta = _activar(client, cliente_a, "corta-123")
    _antes_del_campo(respuesta.content.decode())


def test_crear_administrador_avisa_las_reglas_junto_al_enlace():
    salida = io.StringIO()
    call_command(
        "crear_administrador",
        "--rut=12.345.678-5",
        "--nombre=Primera Administradora",
        "--email=admin@ejemplo.test",
        stdout=salida,
    )
    assert f"Contraseña que pedirá el enlace: {REGLAS}" in salida.getvalue()


def test_el_texto_de_las_reglas_sigue_al_largo_configurado(settings):
    assert reglas_contrasena() == REGLAS
    settings.CONTRASENA_LARGO_MINIMO = 14
    assert reglas_contrasena().startswith("Use al menos 14 caracteres.")


def test_una_contrasena_comun_no_se_acepta_ni_en_validate_password(cliente_a):
    with pytest.raises(ValidationError):
        validate_password("123456789", user=cliente_a)
