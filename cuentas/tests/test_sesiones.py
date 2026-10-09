"""Sesiones, "Mi cuenta" y cambio de contraseña (AUT-05, AUT-08, AUT-09)."""

from datetime import timedelta

import pytest
from django.conf import settings as configuracion
from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.models import Session
from django.test import Client
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import Accion
from config.tests.test_configuracion import ENTORNO_VALIDO, _importar_prod
from conftest import CLAVE, RUT_CLIENTE_A, entrar

pytestmark = pytest.mark.django_db

NUEVA = "tornillo-violeta-marea-88"


def _cambiar(cliente_http, actual=CLAVE, nueva=NUEVA, **extra):
    datos = {"old_password": actual, "new_password1": nueva, "new_password2": nueva, **extra}
    return cliente_http.post("/cuenta/", datos)


def test_configuracion_de_las_sesiones():
    assert configuracion.SESSION_COOKIE_AGE == 60 * 60
    assert configuracion.SESSION_SAVE_EVERY_REQUEST is True
    assert configuracion.SESSION_EXPIRE_AT_BROWSER_CLOSE is True
    assert configuracion.SESSION_COOKIE_HTTPONLY is True
    assert configuracion.SESSION_COOKIE_SAMESITE == "Lax"


def test_en_produccion_las_cookies_son_seguras():
    codigo = (
        "import config.settings.prod as p; "
        "print(p.SESSION_COOKIE_SECURE, p.CSRF_COOKIE_SECURE, p.SESSION_COOKIE_HTTPONLY, "
        "p.SESSION_COOKIE_SAMESITE)"
    )
    resultado = _importar_prod(ENTORNO_VALIDO, codigo)
    assert resultado.stdout.split() == ["True", "True", "True", "Lax"], resultado.stderr


def test_la_cookie_de_sesion_es_httponly_samesite_y_sin_fecha_de_vencimiento(
    client, cliente_a_activo
):
    respuesta = entrar(client, RUT_CLIENTE_A)
    cookie = respuesta.cookies[configuracion.SESSION_COOKIE_NAME]
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Lax"
    # Sin "Recordarme": la cookie muere al cerrar el navegador.
    assert cookie["max-age"] == "" and cookie["expires"] == ""


def test_la_sesion_vence_tras_60_minutos_sin_uso_y_cada_uso_la_renueva(client, cliente_a_activo):
    entrar(client, RUT_CLIENTE_A)
    sesion = Session.objects.get()
    restante = sesion.expire_date - timezone.now()
    assert timedelta(minutes=59) < restante <= timedelta(minutes=60)

    # A los 50 minutos sigue vigente, y usarla corre el vencimiento.
    Session.objects.update(expire_date=timezone.now() + timedelta(minutes=10))
    assert client.get("/portal/").status_code == 200
    assert Session.objects.get().expire_date - timezone.now() > timedelta(minutes=59)

    # Pasado el plazo, la sesión ya no sirve.
    Session.objects.update(expire_date=timezone.now() - timedelta(seconds=1))
    assert client.get("/portal/")["Location"] == "/acceso/?next=/portal/"


def test_mi_cuenta_muestra_los_datos_y_no_ofrece_editarlos(client, cliente_a_activo):
    entrar(client, RUT_CLIENTE_A)
    respuesta = client.get("/cuenta/")
    assert respuesta.status_code == 200
    contenido = respuesta.content.decode()
    for dato in ("Cliente de A", "11.111.111-1", "cliente.a@ejemplo.test"):
        assert dato in contenido
    assert "Estos datos solo los puede modificar un administrador." in contenido
    # Los únicos campos del formulario son los de la contraseña.
    assert 'name="email"' not in contenido and 'name="rut"' not in contenido
    assert 'name="nombre"' not in contenido
    assert 'class="lateral-enlace" href="/cuenta/" aria-current="page"' in contenido
    assert "no-store" in respuesta["Cache-Control"]


def test_el_cliente_no_puede_cambiar_su_correo_ni_su_rut_con_un_post_hecho_a_mano(
    client, cliente_a_activo
):
    """El correo es por donde llega la recuperación: solo lo cambia un administrador."""
    entrar(client, RUT_CLIENTE_A)
    respuesta = _cambiar(
        client,
        email="atacante@malicioso.example",
        rut="22.222.222-2",
        nombre="Otro Nombre",
        rol="administrador",
        is_active="",
    )
    assert respuesta.status_code == 302
    assert client.post("/cuenta/", {"email": "atacante@malicioso.example"}).status_code == 200

    cliente_a_activo.refresh_from_db()
    assert cliente_a_activo.email == "cliente.a@ejemplo.test"
    assert cliente_a_activo.rut == "111111111"
    assert cliente_a_activo.nombre == "Cliente de A"
    assert cliente_a_activo.rol == "cliente" and cliente_a_activo.is_active is True


def test_cambiar_la_contrasena_pide_la_actual(client, cliente_a_activo):
    entrar(client, RUT_CLIENTE_A)
    respuesta = _cambiar(client, actual="no-es-la-actual-123")
    assert respuesta.status_code == 200
    assert "Revise los campos marcados" in respuesta.content.decode()
    cliente_a_activo.refresh_from_db()
    assert cliente_a_activo.check_password(CLAVE)
    assert not EventoAuditoria.objects.filter(accion=Accion.CAMBIO_CONTRASENA).exists()


def test_cambiar_la_contrasena_cierra_las_demas_sesiones_y_conserva_la_actual(
    client, cliente_a_activo
):
    otra = Client()
    entrar(otra, RUT_CLIENTE_A)
    entrar(client, RUT_CLIENTE_A)

    respuesta = _cambiar(client)
    assert respuesta.status_code == 302 and respuesta["Location"] == "/cuenta/"
    cliente_a_activo.refresh_from_db()
    assert cliente_a_activo.check_password(NUEVA)
    assert cliente_a_activo.password.startswith("argon2$argon2id$")

    pagina = client.get("/cuenta/")
    assert pagina.status_code == 200
    assert "Su contraseña quedó cambiada" in pagina.content.decode()
    assert otra.get("/portal/")["Location"] == "/acceso/?next=/portal/"

    evento = EventoAuditoria.objects.get(accion=Accion.CAMBIO_CONTRASENA)
    assert evento.actor == cliente_a_activo
    assert NUEVA not in evento.detalle and CLAVE not in evento.detalle


def test_la_contrasena_nueva_pasa_por_los_validadores(client, cliente_a_activo):
    entrar(client, RUT_CLIENTE_A)
    for debil, mensaje in (
        ("corta-1", "por lo menos 12 caracteres"),
        ("123456789012345", "numérica"),
        ("1q2w3e4r5t6y7u8i", "demasiado común"),
        ("cliente.a@ejemplo.test", "similar"),
    ):
        respuesta = _cambiar(client, nueva=debil)
        assert respuesta.status_code == 200, debil
        assert mensaje in respuesta.content.decode(), debil
    cliente_a_activo.refresh_from_db()
    assert cliente_a_activo.check_password(CLAVE)


def test_varios_fallos_con_la_contrasena_actual_cierran_la_sesion(
    client, cliente_a_activo, settings
):
    settings.ACCESO_INTENTOS_MAXIMOS = 3
    entrar(client, RUT_CLIENTE_A)
    assert _cambiar(client, actual="no-es-la-actual-1").status_code == 200
    assert _cambiar(client, actual="no-es-la-actual-2").status_code == 200
    respuesta = _cambiar(client, actual="no-es-la-actual-3")
    assert respuesta.status_code == 302 and respuesta["Location"] == "/acceso/"
    assert SESSION_KEY not in client.session
    assert "Demasiados intentos" in client.get("/acceso/").content.decode()


def test_mi_cuenta_del_administrador_usa_la_estructura_del_panel(cliente_http_admin):
    contenido = cliente_http_admin.get("/cuenta/").content.decode()
    assert "Administradora de Prueba" in contenido and "12.345.678-5" in contenido
    assert 'class="lateral-enlace" href="/panel/"' in contenido
    assert 'href="/portal/"' not in contenido
