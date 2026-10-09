"""2FA de administradores y admin de Django (AUT-10, ADM-12; prueba 9 de la sección 12.2)."""

import io
import re
import time

import pytest
from django.core.management import call_command
from django.test import Client
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from auditoria.models import EventoAuditoria
from auditoria.services import Accion
from conftest import CLAVE, RUT_ADMINISTRADOR, RUT_CLIENTE_A, codigo_totp, entrar
from cuentas import services
from cuentas.models import EnlaceAcceso, Usuario

pytestmark = pytest.mark.django_db

NUEVA = "tornillo-violeta-marea-88"
ADMIN_DJANGO = "/admin-tecnico/"


def _usar_enlace(cliente_http, usuario, tipo=EnlaceAcceso.Tipo.ACTIVACION, clave=NUEVA):
    """Define la contraseña con un enlace nuevo, como haría la persona al recibirlo."""
    _, token = services.generar_enlace(usuario, tipo)
    ruta = "activar" if tipo == EnlaceAcceso.Tipo.ACTIVACION else "restablecer"
    return cliente_http.post(f"/{ruta}/{token}/", {"new_password1": clave, "new_password2": clave})


def _eventos(accion):
    return EventoAuditoria.objects.filter(accion=accion)


# --- Enrolamiento ligado al enlace -------------------------------------------------------


def test_quien_entra_solo_con_la_contrasena_no_puede_enrolar_su_dispositivo(
    client, administrador_activo
):
    """Conocer la contraseña de un administrador sin 2FA no basta para tomar su cuenta."""
    respuesta = entrar(client, RUT_ADMINISTRADOR)
    assert respuesta["Location"] == "/acceso/verificacion/?next=/panel/"
    assert client.get("/acceso/verificacion/")["Location"] == "/acceso/2fa/configurar/"

    pagina = client.get("/acceso/2fa/configurar/")
    assert pagina.status_code == 403
    contenido = pagina.content.decode()
    assert "Solicite un enlace nuevo" in contenido
    # No se muestra ningún código ni clave, y no se crea ningún dispositivo.
    assert 'class="qr"' not in contenido
    assert not TOTPDevice.objects.exists()

    # Tampoco por POST directo.
    assert client.post("/acceso/2fa/configurar/", {"codigo": "123456"}).status_code == 403
    assert not TOTPDevice.objects.exists()
    assert client.get("/panel/")["Location"] == "/acceso/verificacion/?next=/panel/"
    assert client.get("/cuenta/")["Location"] == "/acceso/verificacion/?next=/cuenta/"


def test_tras_usar_el_enlace_de_activacion_el_administrador_enrola_y_entra(client, administrador):
    respuesta = _usar_enlace(client, administrador)
    assert respuesta["Location"] == "/acceso/verificacion/?next=/panel/"
    assert client.get("/panel/").status_code == 302

    pagina = client.get("/acceso/2fa/configurar/")
    assert pagina.status_code == 200
    contenido = pagina.content.decode()
    assert "<svg width=" in contenido and 'class="qr"' in contenido
    # Compatible con la CSP: sin estilos ni scripts en línea, y sin imágenes externas.
    assert " style=" not in contenido and "<img" not in contenido
    dispositivo = TOTPDevice.objects.get()
    assert dispositivo.confirmed is False and dispositivo.user == administrador
    # Recargar la página no cambia la clave que ya se escaneó.
    client.get("/acceso/2fa/configurar/")
    assert TOTPDevice.objects.get().key == dispositivo.key

    # Un código incorrecto no confirma nada.
    errado = client.post("/acceso/2fa/configurar/", {"codigo": "000000"})
    assert errado.status_code == 200 and "El código no es correcto." in errado.content.decode()
    assert TOTPDevice.objects.get().confirmed is False

    # django-otp impone una espera tras un fallo: se quita para no dormir la prueba.
    TOTPDevice.objects.update(throttling_failure_count=0, throttling_failure_timestamp=None)
    correcto = client.post("/acceso/2fa/configurar/", {"codigo": codigo_totp(dispositivo)})
    assert correcto.status_code == 302 and correcto["Location"] == "/acceso/2fa/codigos/"
    assert TOTPDevice.objects.get().confirmed is True

    codigos = client.get("/acceso/2fa/codigos/")
    assert codigos.status_code == 200
    mostrados = re.findall(r"<li>([a-z0-9]{8})</li>", codigos.content.decode())
    assert len(mostrados) == 10 == len(set(mostrados))
    assert set(mostrados) == set(StaticToken.objects.values_list("token", flat=True))
    assert "no-store" in codigos["Cache-Control"]
    # Se muestran una sola vez.
    assert client.get("/acceso/2fa/codigos/").status_code == 302

    assert client.get("/panel/").status_code == 200
    assert _eventos(Accion.DOS_FACTORES_ENROLADO).get().actor == administrador
    # El permiso se consumió: no puede enrolar otro dispositivo en esta sesión.
    assert client.get("/acceso/2fa/configurar/")["Location"] == "/acceso/verificacion/"


def test_el_permiso_para_enrolar_vence(client, administrador, settings):
    _usar_enlace(client, administrador)
    sesion = client.session
    sesion["enrolamiento_2fa"] = {**sesion["enrolamiento_2fa"], "hasta": time.time() - 1}
    sesion.save()
    assert client.get("/acceso/2fa/configurar/").status_code == 403


def test_el_permiso_no_pasa_a_otra_sesion_ni_sobrevive_al_cierre(client, administrador):
    _usar_enlace(client, administrador)
    assert client.get("/acceso/2fa/configurar/").status_code == 200
    # Otra sesión con la misma contraseña recién definida.
    otra = Client()
    entrar(otra, RUT_ADMINISTRADOR, NUEVA)
    assert otra.get("/acceso/2fa/configurar/").status_code == 403
    # Y si la sesión original se cierra, el permiso se pierde con ella.
    client.post("/salir/")
    entrar(client, RUT_ADMINISTRADOR, NUEVA)
    assert client.get("/acceso/2fa/configurar/").status_code == 403


def test_un_administrador_con_2fa_no_puede_enrolar_otro_aunque_use_un_enlace(
    client, administrador_activo, totp
):
    respuesta = _usar_enlace(client, administrador_activo, EnlaceAcceso.Tipo.RESTABLECIMIENTO)
    assert respuesta["Location"] == "/acceso/verificacion/?next=/panel/"
    assert client.get("/acceso/2fa/configurar/")["Location"] == "/acceso/verificacion/"
    assert TOTPDevice.objects.count() == 1
    assert client.get("/panel/").status_code == 302


def test_un_cliente_no_recibe_permiso_ni_ve_las_pantallas_de_2fa(client, cliente_a):
    assert _usar_enlace(client, cliente_a)["Location"] == "/portal/"
    assert "enrolamiento_2fa" not in client.session
    for ruta in ("/acceso/verificacion/", "/acceso/2fa/configurar/", "/acceso/2fa/codigos/"):
        assert client.get(ruta).status_code == 404, ruta


def test_las_pantallas_de_2fa_exigen_sesion(client):
    for ruta in ("/acceso/verificacion/", "/acceso/2fa/configurar/", "/acceso/2fa/codigos/"):
        assert client.get(ruta)["Location"] == f"/acceso/?next={ruta}", ruta


# --- Verificación ---------------------------------------------------------------------


def test_un_administrador_sin_2fa_verificado_no_entra_al_panel(client, administrador_activo, totp):
    """Prueba 9 de la sección 12.2."""
    entrar(client, RUT_ADMINISTRADOR)
    for ruta in ("/panel/", "/cuenta/"):
        respuesta = client.get(ruta)
        assert respuesta["Location"] == f"/acceso/verificacion/?next={ruta}"
    assert client.get("/portal/").status_code == 404

    pagina = client.get("/acceso/verificacion/?next=/panel/")
    assert pagina.status_code == 200
    assert 'autocomplete="one-time-code"' in pagina.content.decode()

    errado = client.post("/acceso/verificacion/", {"codigo": "000000"})
    assert errado.status_code == 200 and "El código no es correcto." in errado.content.decode()
    assert client.get("/panel/").status_code == 302
    assert _eventos(Accion.DOS_FACTORES_FALLIDO).count() == 1

    TOTPDevice.objects.update(throttling_failure_count=0, throttling_failure_timestamp=None)
    correcto = client.post(
        "/acceso/verificacion/", {"codigo": codigo_totp(totp), "next": "/panel/"}
    )
    assert correcto.status_code == 302 and correcto["Location"] == "/panel/"
    assert client.get("/panel/").status_code == 200
    assert client.get("/cuenta/").status_code == 200
    assert _eventos(Accion.DOS_FACTORES_VERIFICADO).get().actor == administrador_activo
    # Con el factor verificado, la pantalla de verificación ya no se muestra.
    assert client.get("/acceso/verificacion/")["Location"] == "/panel/"


def test_la_verificacion_vale_solo_para_la_sesion_que_la_hizo(client, administrador_activo, totp):
    entrar(client, RUT_ADMINISTRADOR)
    client.post("/acceso/verificacion/", {"codigo": codigo_totp(totp)})
    assert client.get("/panel/").status_code == 200
    otra = Client()
    entrar(otra, RUT_ADMINISTRADOR)
    assert otra.get("/panel/").status_code == 302


def test_un_codigo_totp_no_se_puede_reutilizar(client, administrador_activo, totp):
    codigo = codigo_totp(totp)
    entrar(client, RUT_ADMINISTRADOR)
    assert client.post("/acceso/verificacion/", {"codigo": codigo}).status_code == 302
    otra = Client()
    entrar(otra, RUT_ADMINISTRADOR)
    assert otra.post("/acceso/verificacion/", {"codigo": codigo}).status_code == 200
    assert otra.get("/panel/").status_code == 302


def test_tras_un_codigo_errado_hay_que_esperar(client, administrador_activo, totp):
    entrar(client, RUT_ADMINISTRADOR)
    client.post("/acceso/verificacion/", {"codigo": "000000"})
    # Incluso el código correcto se rechaza durante la espera.
    respuesta = client.post("/acceso/verificacion/", {"codigo": codigo_totp(totp)})
    assert respuesta.status_code == 200
    assert "Espere un momento antes de ingresar otro código" in respuesta.content.decode()
    assert client.get("/panel/").status_code == 302
    assert _eventos(Accion.DOS_FACTORES_FALLIDO).filter(detalle__startswith="En espera").exists()


def test_un_codigo_de_recuperacion_sirve_una_sola_vez(
    client, administrador_activo, totp, codigos_de_recuperacion
):
    entrar(client, RUT_ADMINISTRADOR)
    respuesta = client.post("/acceso/verificacion/", {"codigo": " AAAA-1111 "})
    assert respuesta.status_code == 302 and respuesta["Location"] == "/panel/"
    panel = client.get("/panel/")
    assert panel.status_code == 200
    assert "Le quedan 1 sin usar" in panel.content.decode()
    assert list(StaticToken.objects.values_list("token", flat=True)) == ["bbbb2222"]
    assert _eventos(Accion.DOS_FACTORES_RECUPERACION).get().detalle == "Quedan 1"
    # Usarlo no sumó fallos al TOTP.
    totp.refresh_from_db()
    assert totp.throttling_failure_count == 0

    otra = Client()
    entrar(otra, RUT_ADMINISTRADOR)
    assert otra.post("/acceso/verificacion/", {"codigo": "aaaa1111"}).status_code == 200
    assert otra.get("/panel/").status_code == 302


# --- Restablecer el 2FA ---------------------------------------------------------------


def test_restablecer_2fa_elimina_los_dispositivos_y_entrega_un_enlace_para_enrolar(
    cliente_http_admin, administrador_activo, totp, codigos_de_recuperacion
):
    assert cliente_http_admin.get("/panel/").status_code == 200
    salida = io.StringIO()
    call_command("restablecer_2fa", RUT_ADMINISTRADOR, stdout=salida)

    assert not TOTPDevice.objects.exists() and not StaticDevice.objects.exists()
    assert _eventos(Accion.DOS_FACTORES_RESTABLECIDO).get().objeto_uuid == administrador_activo.uuid
    # La sesión que estaba verificada deja de estarlo.
    assert cliente_http_admin.get("/panel/").status_code == 302
    # Con la contraseña sola no puede volver a enrolar.
    solo_clave = Client()
    entrar(solo_clave, RUT_ADMINISTRADOR)
    assert solo_clave.get("/acceso/2fa/configurar/").status_code == 403

    url = re.search(r"http://testserver(/restablecer/\S+/)", salida.getvalue()).group(1)
    nuevo = Client()
    respuesta = nuevo.post(url, {"new_password1": NUEVA, "new_password2": NUEVA})
    assert respuesta["Location"] == "/acceso/verificacion/?next=/panel/"
    assert nuevo.get("/acceso/2fa/configurar/").status_code == 200
    dispositivo = TOTPDevice.objects.get()
    assert (
        nuevo.post("/acceso/2fa/configurar/", {"codigo": codigo_totp(dispositivo)})["Location"]
        == "/acceso/2fa/codigos/"
    )
    assert nuevo.get("/panel/").status_code == 200


def test_restablecer_2fa_rechaza_un_rut_que_no_es_de_un_administrador(cliente_a_activo):
    from django.core.management.base import CommandError

    for rut in (RUT_CLIENTE_A, "11.111.111-2", "9.876.543-3"):
        with pytest.raises(CommandError):
            call_command("restablecer_2fa", rut, stdout=io.StringIO())
    assert not EnlaceAcceso.objects.exists()


# --- Admin de Django (ADM-12) ---------------------------------------------------------


@pytest.fixture
def superusuario(db):
    usuario = Usuario.objects.create_superuser(
        "7.777.777-6", password=CLAVE, nombre="Soporte Técnico", email="soporte@ejemplo.test"
    )
    dispositivo = TOTPDevice.objects.create(user=usuario, name="Aplicación", confirmed=True)
    return usuario, dispositivo


def test_el_admin_de_django_exige_superusuario_tecnico_con_2fa(
    client, superusuario, cliente_a_activo, cliente_http_admin
):
    usuario, dispositivo = superusuario
    # Anónimo: al formulario de acceso de la aplicación, no a uno propio del admin.
    anonimo = Client()
    respuesta = anonimo.get(ADMIN_DJANGO, follow=True)
    assert respuesta.redirect_chain[-1][0].startswith("/acceso/?next=")
    assert 'name="rut"' in respuesta.content.decode()

    # Cliente con sesión: 404.
    cliente = Client()
    entrar(cliente, RUT_CLIENTE_A)
    assert cliente.get(ADMIN_DJANGO, follow=True).status_code == 404

    # Administrador del negocio verificado, pero sin privilegios técnicos: 404.
    assert cliente_http_admin.get(ADMIN_DJANGO, follow=True).status_code == 404

    # Superusuario con contraseña pero sin segundo factor: a la verificación.
    tecnico = Client()
    entrar(tecnico, usuario.rut)
    respuesta = tecnico.get(ADMIN_DJANGO, follow=True)
    assert respuesta.redirect_chain[-1][0].startswith("/acceso/verificacion/?next=")

    # Con el segundo factor verificado, entra.
    respuesta = tecnico.post(
        "/acceso/verificacion/", {"codigo": codigo_totp(dispositivo), "next": ADMIN_DJANGO}
    )
    assert respuesta["Location"] == ADMIN_DJANGO
    indice = tecnico.get(ADMIN_DJANGO)
    assert indice.status_code == 200
    assert "Administración técnica" in indice.content.decode()


def test_el_admin_de_django_no_permite_fijar_contrasenas_ni_tocar_la_auditoria(
    superusuario, cliente_a_activo
):
    from django.contrib import admin
    from django.test import RequestFactory

    usuario, _ = superusuario
    request = RequestFactory().get(ADMIN_DJANGO)
    request.user = usuario

    admin_usuario = admin.site._registry[Usuario]
    assert "password" not in admin_usuario.get_fields(request, cliente_a_activo)
    assert admin_usuario.has_add_permission(request) is False
    assert admin_usuario.has_delete_permission(request) is False

    admin_evento = admin.site._registry[EventoAuditoria]
    assert admin_evento.has_add_permission(request) is False
    assert admin_evento.has_change_permission(request) is False
    assert admin_evento.has_delete_permission(request) is False

    admin_enlace = admin.site._registry[EnlaceAcceso]
    assert "token_hash" not in admin_enlace.get_fields(request)
    assert admin_enlace.has_change_permission(request) is False
