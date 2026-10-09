"""Acceso con RUT y contraseña, mensajes genéricos y cierre de sesión (AUT-01 a AUT-03, AUT-09)."""

import re
from unittest import mock

import pytest
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.hashers import Argon2PasswordHasher
from django.db import connection
from django.test.utils import CaptureQueriesContext

from auditoria.models import EventoAuditoria
from auditoria.services import Accion
from conftest import (
    CLAVE,
    RUT_ADMINISTRADOR,
    RUT_CLIENTE_A,
    RUT_CLIENTE_B,
    RUT_INEXISTENTE,
    entrar,
)
from core import rut as utilidades_rut
from cuentas.models import Usuario

pytestmark = pytest.mark.django_db

MENSAJE = "RUT o contraseña incorrectos."


def _eventos(accion):
    return EventoAuditoria.objects.filter(accion=accion)


def _normalizar(respuesta, rut):
    """El cuerpo sin lo que cambia por diseño: el token CSRF y el RUT que se escribió."""
    cuerpo = respuesta.content.decode()
    cuerpo = re.sub(r'name="csrfmiddlewaretoken" value="[^"]+"', "", cuerpo)
    cuerpo = re.sub(r'"X-CSRFToken": "[^"]+"', "", cuerpo)
    return cuerpo.replace(f'value="{rut}"', 'value="RUT"')


def test_el_formulario_de_acceso_sigue_la_referencia_y_no_ofrece_recordarme(client):
    respuesta = client.get("/acceso/")
    assert respuesta.status_code == 200
    contenido = respuesta.content.decode()
    assert "<h1" in contenido and "Acceso clientes" in contenido
    assert 'name="rut"' in contenido and 'placeholder="12.345.678-5"' in contenido
    assert '<input type="password" name="contrasena"' in contenido
    # Botón accesible para mostrar la contraseña (AUT-01).
    assert 'data-alterna-contrasena="id_contrasena"' in contenido
    assert 'aria-label="Mostrar contraseña"' in contenido
    assert 'href="/recuperar/"' in contenido and "¿Olvidó su contraseña?" in contenido
    assert "Acceso restringido solo para clientes autorizados" in contenido
    assert 'name="csrfmiddlewaretoken"' in contenido
    assert 'content="noindex"' in contenido
    # Diferencias con el mockup: sin "Recordarme" y con trato de usted.
    assert "ecordar" not in contenido
    assert 'type="checkbox"' not in contenido
    assert "Ingresa con tu" not in contenido
    assert "no-store" in respuesta["Cache-Control"]


@pytest.mark.parametrize(
    "escrito",
    [
        "11.111.111-1",
        "111111111",
        "11111111-1",
        "11 111 111-1",
        "  11.111.111-1  ",
        "011.111.111-1",
    ],
)
def test_el_rut_se_acepta_con_o_sin_puntos_y_guion(client, cliente_a_activo, escrito):
    respuesta = entrar(client, escrito)
    assert respuesta.status_code == 302
    assert respuesta["Location"] == "/portal/"


@pytest.mark.parametrize("letra", ["K", "k"])
def test_el_rut_con_k_se_acepta_en_mayuscula_y_en_minuscula(client, empresa_a, letra):
    cuerpo = next(
        n for n in range(10_000_000, 10_000_100) if utilidades_rut.digito_verificador(n) == "K"
    )
    usuario = Usuario.objects.create_user(
        f"{cuerpo}K", password=CLAVE, nombre="Con K", rol=Usuario.Rol.CLIENTE, empresa=empresa_a
    )
    respuesta = entrar(client, f"{cuerpo}-{letra}")
    assert respuesta.status_code == 302
    assert int(client.session[SESSION_KEY]) == usuario.pk


def test_el_cliente_entra_al_portal_y_queda_registrado(client, cliente_a_activo):
    client.get("/acceso/")
    sesion_anonima = client.session.session_key
    respuesta = entrar(client, RUT_CLIENTE_A, REMOTE_ADDR="203.0.113.7")

    assert respuesta.status_code == 302 and respuesta["Location"] == "/portal/"
    assert int(client.session[SESSION_KEY]) == cliente_a_activo.pk
    # El identificador de sesión rota al iniciar sesión (AUT-09).
    assert client.session.session_key != sesion_anonima
    cliente_a_activo.refresh_from_db()
    assert cliente_a_activo.last_login is not None

    evento = _eventos(Accion.ACCESO_EXITOSO).get()
    assert evento.actor == cliente_a_activo
    assert evento.empresa == cliente_a_activo.empresa
    assert evento.ip == "203.0.113.7"
    assert client.get("/portal/").status_code == 200


def test_el_administrador_pasa_primero_por_el_segundo_factor(client, administrador_activo, totp):
    respuesta = entrar(client, RUT_ADMINISTRADOR)
    assert respuesta.status_code == 302
    assert respuesta["Location"] == "/acceso/verificacion/?next=/panel/"


def test_credenciales_invalidas_muestran_el_mensaje_generico(client, cliente_a_activo):
    respuesta = entrar(client, RUT_CLIENTE_A, "clave-equivocada-123")
    assert respuesta.status_code == 200
    contenido = respuesta.content.decode()
    assert MENSAJE in contenido
    assert 'role="alert"' in contenido and 'aria-live="assertive"' in contenido
    # Conserva el RUT escrito y nunca devuelve la contraseña.
    assert f'value="{RUT_CLIENTE_A}"' in contenido
    assert "clave-equivocada-123" not in contenido
    assert SESSION_KEY not in client.session

    evento = _eventos(Accion.ACCESO_FALLIDO).get()
    assert evento.rut_intentado == "111111111"
    assert evento.actor is None
    assert evento.empresa == cliente_a_activo.empresa


@pytest.fixture
def casos_de_fallo(cliente_a_activo, cliente_b_activo, administrador, empresa_a, empresa_b):
    """Un RUT por cada motivo de rechazo. Devuelve {motivo: (rut, contraseña)}."""
    inactivo = Usuario.objects.create_user(
        "5.555.555-9", password=CLAVE, nombre="Inactivo", rol=Usuario.Rol.CLIENTE, empresa=empresa_a
    )
    inactivo.is_active = False
    inactivo.save()
    empresa_b.activa = False
    empresa_b.save()
    return {
        "clave errada": (RUT_CLIENTE_A, "clave-equivocada-123"),
        "rut inexistente": (RUT_INEXISTENTE, CLAVE),
        "cuenta inactiva": ("5.555.555-9", CLAVE),
        "empresa inactiva": (RUT_CLIENTE_B, CLAVE),
        # El administrador de la base no tiene contraseña utilizable todavía.
        "cuenta sin activar": (RUT_ADMINISTRADOR, CLAVE),
    }


def test_la_respuesta_es_identica_exista_o_no_el_rut(client, casos_de_fallo):
    """Prueba 7 de la sección 12.2: mismo código y mismo cuerpo en todos los casos."""
    cuerpos = {}
    for motivo, (rut, clave) in casos_de_fallo.items():
        respuesta = entrar(client, rut, clave)
        assert respuesta.status_code == 200, motivo
        assert SESSION_KEY not in client.session, motivo
        cuerpos[motivo] = _normalizar(respuesta, rut)
    assert MENSAJE in cuerpos["clave errada"]
    for motivo, cuerpo in cuerpos.items():
        assert cuerpo == cuerpos["clave errada"], motivo
    # Un RUT con dígito verificador incorrecto recibe la misma respuesta.
    invalido = entrar(client, "11.111.111-2", CLAVE)
    assert _normalizar(invalido, "11.111.111-2") == cuerpos["clave errada"]


def test_cada_intento_ejecuta_exactamente_una_verificacion_de_contrasena(client, casos_de_fallo):
    """AUT-02: el tiempo no delata el motivo, porque el trabajo costoso es siempre el mismo."""
    casos = {**casos_de_fallo, "rut inválido": ("11.111.111-2", CLAVE)}
    for motivo, (rut, clave) in casos.items():
        with (
            mock.patch.object(
                Argon2PasswordHasher,
                "verify",
                autospec=True,
                side_effect=Argon2PasswordHasher.verify,
            ) as verificar,
            mock.patch.object(
                Argon2PasswordHasher,
                "encode",
                autospec=True,
                side_effect=Argon2PasswordHasher.encode,
            ) as cifrar,
        ):
            entrar(client, rut, clave)
        assert verificar.call_count + cifrar.call_count == 1, motivo


def test_cada_intento_fallido_hace_las_mismas_consultas(client, casos_de_fallo):
    consultas = {}
    for motivo, (rut, clave) in casos_de_fallo.items():
        with CaptureQueriesContext(connection) as contexto:
            entrar(client, rut, clave)
        consultas[motivo] = len(contexto)
    assert len(set(consultas.values())) == 1, consultas
    # Y todos dejan su evento, con el RUT intentado.
    assert EventoAuditoria.objects.filter(accion=Accion.ACCESO_FALLIDO).count() == len(consultas)


def test_campos_vacios_no_llegan_a_evaluar_credenciales(client):
    respuesta = client.post("/acceso/", {"rut": "", "contrasena": ""})
    assert respuesta.status_code == 200
    assert "Este campo es obligatorio" in respuesta.content.decode()
    assert not EventoAuditoria.objects.exists()


def test_la_contrasena_escrita_en_el_campo_del_rut_no_queda_en_la_auditoria(client):
    entrar(client, "MiClaveSecreta-2026", "otra-cosa-123456")
    evento = _eventos(Accion.ACCESO_FALLIDO).get()
    assert evento.rut_intentado == ""
    assert "MiClaveSecreta" not in evento.detalle


def test_el_destino_solicitado_solo_se_respeta_si_es_de_la_aplicacion(client, cliente_a_activo):
    respuesta = client.post(
        "/acceso/?next=/cuenta/", {"rut": RUT_CLIENTE_A, "contrasena": CLAVE, "next": "/cuenta/"}
    )
    assert respuesta["Location"] == "/cuenta/"
    client.post("/salir/")
    for externo in ("https://malicioso.example/x", "//malicioso.example/x"):
        respuesta = client.post(
            "/acceso/", {"rut": RUT_CLIENTE_A, "contrasena": CLAVE, "next": externo}
        )
        assert respuesta["Location"] == "/portal/"
        client.post("/salir/")


def test_quien_ya_tiene_sesion_va_directo_a_su_inicio(client, cliente_a_activo):
    entrar(client, RUT_CLIENTE_A)
    respuesta = client.get("/acceso/")
    assert respuesta.status_code == 302 and respuesta["Location"] == "/portal/"


def test_el_cierre_de_sesion_es_solo_por_post(client, cliente_a_activo):
    entrar(client, RUT_CLIENTE_A)
    assert client.get("/salir/").status_code == 405
    assert SESSION_KEY in client.session

    respuesta = client.post("/salir/")
    assert respuesta.status_code == 302 and respuesta["Location"] == "/acceso/"
    assert SESSION_KEY not in client.session
    assert _eventos(Accion.CIERRE_SESION).get().actor == cliente_a_activo
    assert client.get("/portal/").status_code == 302


def test_el_portal_muestra_el_menu_real_y_el_cierre_por_post(client, cliente_a_activo):
    entrar(client, RUT_CLIENTE_A)
    contenido = client.get("/portal/").content.decode()
    assert "Hola, Empresa A de Prueba SpA" in contenido
    assert "RUT: 76.111.111-6" in contenido
    assert 'class="lateral-enlace" href="/portal/" aria-current="page"' in contenido
    assert 'href="/cuenta/"' in contenido
    assert '<form class="mt-4 lg:mt-auto lg:pt-4" method="post" action="/salir/">' in contenido
    assert 'content="noindex"' in contenido


@pytest.mark.parametrize(
    "ruta", ["/acceso/", "/recuperar/", "/recuperar/enviado/", "/activar/un-token-invalido/"]
)
def test_las_pantallas_de_acceso_no_llevan_estilos_ni_scripts_en_linea(client, ruta):
    """La CSP los bloquearía (SEG-02)."""
    respuesta = client.get(ruta)
    contenido = respuesta.content.decode()
    for prohibido in (" style=", "<style", "<script>", " onclick=", "<img"):
        assert prohibido not in contenido, (ruta, prohibido)
    assert "script-src 'self'" in respuesta["Content-Security-Policy"]
    assert 'content="noindex"' in contenido
