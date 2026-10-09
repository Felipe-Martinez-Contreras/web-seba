"""Enlaces de activación y de restablecimiento (AUT-06, AUT-07; prueba 8 de la sección 12.2)."""

import hashlib
from datetime import timedelta

import pytest
from django.contrib.auth import SESSION_KEY
from django.test import Client
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import Accion
from conftest import CLAVE, RUT_CLIENTE_A, entrar
from cuentas import services
from cuentas.models import EnlaceAcceso

pytestmark = pytest.mark.django_db

ACTIVACION = EnlaceAcceso.Tipo.ACTIVACION
RESTABLECIMIENTO = EnlaceAcceso.Tipo.RESTABLECIMIENTO
NUEVA = "tornillo-violeta-marea-88"
INVALIDO = "Este enlace no es válido, ya se usó o venció."


def _definir(cliente_http, url, clave=NUEVA, repetir=None):
    return cliente_http.post(
        url, {"new_password1": clave, "new_password2": clave if repetir is None else repetir}
    )


def _avanzar_el_reloj(monkeypatch, delta):
    """Mueve el reloj de los servicios de cuentas, sin tocar el del resto de Django."""
    real = timezone.now

    class Reloj:
        now = staticmethod(lambda: real() + delta)

    monkeypatch.setattr(services, "timezone", Reloj)


def test_el_enlace_guarda_solo_el_hash_del_token_y_no_identifica_al_usuario(cliente_a):
    enlace, token = services.generar_enlace(cliente_a, ACTIVACION)
    assert len(token) >= 43
    assert enlace.token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert token not in enlace.token_hash
    url = services.url_del_enlace(ACTIVACION, token)
    assert url == f"http://testserver/activar/{token}/"
    # Ni el ID, ni el UUID, ni el RUT del usuario aparecen en la dirección.
    for dato in (str(cliente_a.pk) + "/", str(cliente_a.uuid), cliente_a.rut):
        assert dato not in url.removeprefix("http://testserver")


def test_la_activacion_define_la_contrasena_y_deja_al_cliente_en_su_portal(client, cliente_a):
    _, token = services.generar_enlace(cliente_a, ACTIVACION)
    url = f"/activar/{token}/"

    pagina = client.get(url)
    assert pagina.status_code == 200
    contenido = pagina.content.decode()
    assert "Active su cuenta" in contenido and 'content="noindex"' in contenido
    assert "no-store" in pagina["Cache-Control"]

    respuesta = _definir(client, url)
    assert respuesta.status_code == 302 and respuesta["Location"] == "/portal/"
    cliente_a.refresh_from_db()
    assert cliente_a.check_password(NUEVA)
    assert int(client.session[SESSION_KEY]) == cliente_a.pk
    assert "Su cuenta quedó activada." in client.get("/portal/").content.decode()

    evento = EventoAuditoria.objects.get(accion=Accion.ACTIVACION)
    assert evento.actor == cliente_a and evento.objeto_uuid == cliente_a.uuid
    # Y después puede entrar con el formulario normal.
    assert entrar(Client(), RUT_CLIENTE_A, NUEVA)["Location"] == "/portal/"


def test_el_enlace_es_de_un_solo_uso(client, cliente_a):
    _, token = services.generar_enlace(cliente_a, ACTIVACION)
    url = f"/activar/{token}/"
    assert _definir(client, url).status_code == 302

    otro = Client()
    assert otro.get(url).status_code == 404
    segundo = _definir(otro, url, "otra-clave-distinta-777")
    assert segundo.status_code == 404
    assert INVALIDO in segundo.content.decode()
    cliente_a.refresh_from_db()
    assert cliente_a.check_password(NUEVA)
    assert SESSION_KEY not in otro.session


def test_abrir_el_enlace_no_lo_consume(client, cliente_a):
    """Los filtros de correo abren los enlaces antes que la persona."""
    _, token = services.generar_enlace(cliente_a, ACTIVACION)
    for _ in range(3):
        assert client.get(f"/activar/{token}/").status_code == 200
    assert _definir(client, f"/activar/{token}/").status_code == 302


@pytest.mark.parametrize(
    ("tipo", "ruta", "vigencia"),
    [
        (ACTIVACION, "activar", timedelta(hours=72)),
        (RESTABLECIMIENTO, "restablecer", timedelta(hours=1)),
    ],
)
def test_el_enlace_expira(client, cliente_a_activo, monkeypatch, tipo, ruta, vigencia):
    _, token = services.generar_enlace(cliente_a_activo, tipo)
    url = f"/{ruta}/{token}/"

    _avanzar_el_reloj(monkeypatch, vigencia - timedelta(minutes=1))
    assert client.get(url).status_code == 200

    _avanzar_el_reloj(monkeypatch, vigencia + timedelta(seconds=1))
    assert client.get(url).status_code == 404
    assert _definir(client, url).status_code == 404
    cliente_a_activo.refresh_from_db()
    assert cliente_a_activo.check_password(CLAVE)


def test_un_enlace_alterado_falla(client, cliente_a):
    _, token = services.generar_enlace(cliente_a, ACTIVACION)
    alterado = token[:-1] + ("A" if token[-1] != "A" else "B")
    for url in (
        f"/activar/{alterado}/",
        f"/activar/{token[:-1]}/",
        f"/activar/{token}x/",
        f"/activar/{token.swapcase()}/",
        # El token de activación no sirve en la dirección de restablecimiento.
        f"/restablecer/{token}/",
    ):
        assert client.get(url).status_code == 404, url
        assert _definir(client, url).status_code == 404, url
    cliente_a.refresh_from_db()
    assert not cliente_a.has_usable_password()
    # El original sigue intacto.
    assert client.get(f"/activar/{token}/").status_code == 200


def test_un_enlace_nuevo_invalida_el_anterior(client, cliente_a):
    _, primero = services.generar_enlace(cliente_a, ACTIVACION)
    _, segundo = services.generar_enlace(cliente_a, RESTABLECIMIENTO)
    assert client.get(f"/activar/{primero}/").status_code == 404
    assert client.get(f"/restablecer/{segundo}/").status_code == 200


def test_el_enlace_no_sirve_si_la_cuenta_o_la_empresa_se_desactivan(client, cliente_a, empresa_a):
    _, token = services.generar_enlace(cliente_a, ACTIVACION)
    empresa_a.activa = False
    empresa_a.save()
    assert client.get(f"/activar/{token}/").status_code == 404
    empresa_a.activa = True
    empresa_a.save()
    cliente_a.is_active = False
    cliente_a.save()
    assert _definir(client, f"/activar/{token}/").status_code == 404


@pytest.mark.parametrize(
    ("clave", "repetir", "mensaje"),
    [
        ("corta-1", None, "por lo menos 12 caracteres"),
        ("123456789012345", None, "numérica"),
        ("1q2w3e4r5t6y7u8i", None, "demasiado común"),
        (NUEVA, "no-coincide-con-la-otra", "no coinciden"),
    ],
)
def test_una_contrasena_debil_se_rechaza_sin_consumir_el_enlace(
    client, cliente_a, clave, repetir, mensaje
):
    _, token = services.generar_enlace(cliente_a, ACTIVACION)
    respuesta = _definir(client, f"/activar/{token}/", clave, repetir)
    assert respuesta.status_code == 200
    assert mensaje in respuesta.content.decode()
    cliente_a.refresh_from_db()
    assert not cliente_a.has_usable_password()
    assert EnlaceAcceso.objects.get().usado_en is None
    assert _definir(client, f"/activar/{token}/").status_code == 302


def test_restablecer_cierra_la_sesion_abierta_en_otro_dispositivo(client, cliente_a_activo):
    """Escenario E7."""
    otro_dispositivo = Client()
    entrar(otro_dispositivo, RUT_CLIENTE_A)
    assert otro_dispositivo.get("/portal/").status_code == 200

    _, token = services.generar_enlace(cliente_a_activo, RESTABLECIMIENTO)
    assert _definir(client, f"/restablecer/{token}/")["Location"] == "/portal/"

    assert otro_dispositivo.get("/portal/")["Location"] == "/acceso/?next=/portal/"
    assert client.get("/portal/").status_code == 200
    assert EventoAuditoria.objects.filter(accion=Accion.RESTABLECIMIENTO).count() == 1
    # La contraseña anterior ya no sirve.
    assert entrar(Client(), RUT_CLIENTE_A, CLAVE).status_code == 200


def test_usar_un_enlace_levanta_el_bloqueo_del_rut(client, cliente_a_activo, settings):
    settings.ACCESO_INTENTOS_MAXIMOS = 2
    visitante = Client()
    for _ in range(2):
        entrar(visitante, RUT_CLIENTE_A, "clave-equivocada-123")
    _, token = services.generar_enlace(cliente_a_activo, RESTABLECIMIENTO)
    _definir(client, f"/restablecer/{token}/")
    assert entrar(visitante, RUT_CLIENTE_A, NUEVA).status_code == 302


def test_ni_el_token_ni_la_contrasena_quedan_en_la_auditoria(client, cliente_a):
    _, token = services.generar_enlace(cliente_a, ACTIVACION)
    _definir(client, f"/activar/{token}/")
    assert EventoAuditoria.objects.filter(accion=Accion.ENLACE_GENERADO).exists()
    for evento in EventoAuditoria.objects.all():
        texto = " ".join(str(valor) for valor in vars(evento).values())
        assert token not in texto
        assert NUEVA not in texto
        assert "/activar/" not in texto
