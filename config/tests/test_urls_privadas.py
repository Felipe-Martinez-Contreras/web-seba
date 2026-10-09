"""Recorre todas las URL del proyecto (SEG-04, SEG-03; pruebas 1 y 12 de la sección 12.2).

Solo lo que está en la lista pública explícita puede responder sin sesión. Una vista nueva
que no herede de un mixin de rol hace fallar esta prueba sin que nadie la agregue aquí.
"""

import re
import uuid

import pytest
from django.test import Client
from django.urls import URLPattern, URLResolver, get_resolver
from django.urls.resolvers import RegexPattern, RoutePattern

from conftest import RUT_CLIENTE_A, entrar

pytestmark = pytest.mark.django_db

# Nombres completos de las únicas vistas que responden a un visitante sin sesión.
PUBLICAS = {
    "core:salud",
    "cuentas:acceso",
    "cuentas:recuperar",
    "cuentas:recuperar_enviado",
    # Sin un token válido responden 404; con él permiten definir la contraseña.
    "cuentas:activar",
    "cuentas:restablecer",
    # Solo admite POST; cerrar una sesión que no existe no hace nada.
    "cuentas:salir",
}

_VALORES = {
    "UUIDConverter": uuid.UUID("00000000-0000-4000-8000-000000000000"),
    "IntConverter": 1,
}


def _ruta_de(patron):
    """Convierte el patrón en una ruta concreta, con valores de relleno."""
    if isinstance(patron, RoutePattern):

        def relleno(coincidencia):
            conversor = patron.converters[coincidencia.group(1)]
            return str(_VALORES.get(type(conversor).__name__, "x"))

        return re.sub(r"<(?:\w+:)?(\w+)>", relleno, str(patron))
    assert isinstance(patron, RegexPattern)
    texto = str(patron)
    if texto == "(?P<url>.*)$":
        # Última ruta del admin de Django: atrapa cualquier dirección desconocida.
        return "direccion-inexistente/"
    aplicaciones = re.fullmatch(r"\^\(\?P<app_label>([\w|]+)\)/\$", texto)
    if aplicaciones:
        # Índice de una aplicación en el admin de Django.
        return aplicaciones.group(1).split("|")[0] + "/"
    raise AssertionError(f"Patrón con expresión regular no contemplado: {texto}")


def _recorrer(patrones, prefijo="", espacios=()):
    for patron in patrones:
        if isinstance(patron, URLResolver):
            nuevos = (*espacios, patron.namespace) if patron.namespace else espacios
            yield from _recorrer(patron.url_patterns, prefijo + _ruta_de(patron.pattern), nuevos)
        else:
            assert isinstance(patron, URLPattern)
            nombre = ":".join((*espacios, patron.name or ""))
            yield nombre, "/" + prefijo + _ruta_de(patron.pattern), patron.callback


@pytest.fixture(scope="module")
def urls():
    encontradas = list(_recorrer(get_resolver().url_patterns))
    # Si el recorrido dejara de encontrar las URL, la prueba pasaría sin probar nada.
    nombres = {nombre for nombre, _, _ in encontradas}
    assert {"portal:inicio", "panel:inicio", "panel:usuario_desbloquear", "admin:index"} <= nombres
    assert nombres >= PUBLICAS
    return encontradas


def test_un_anonimo_solo_accede_a_la_lista_publica(urls):
    cliente = Client()
    for nombre, ruta, _ in urls:
        if nombre in PUBLICAS:
            continue
        respuesta = cliente.get(ruta)
        if respuesta.status_code == 302:
            destino = respuesta["Location"]
            # El admin de Django redirige dentro de sí mismo hasta su entrada, que lleva al acceso.
            assert destino.startswith(("/acceso/?next=", "/admin-tecnico/")), (nombre, destino)
        else:
            assert respuesta.status_code == 404, (nombre, ruta, respuesta.status_code)
    cadena = cliente.get("/admin-tecnico/", follow=True).redirect_chain
    assert cadena[-1][0].startswith("/acceso/?next=")


def test_las_urls_publicas_responden_sin_sesion(urls):
    cliente = Client()
    esperado = {"cuentas:activar": 404, "cuentas:restablecer": 404, "cuentas:salir": 405}
    for nombre, ruta, _ in urls:
        if nombre in PUBLICAS:
            assert cliente.get(ruta).status_code == esperado.get(nombre, 200), nombre


def test_un_cliente_recibe_404_en_el_panel_y_en_el_admin(urls, cliente_a_activo):
    cliente = Client()
    entrar(cliente, RUT_CLIENTE_A)
    probadas = 0
    for nombre, ruta, _ in urls:
        if not nombre.startswith(("panel:", "admin:")):
            continue
        probadas += 1
        for metodo in (cliente.get, cliente.post):
            respuesta = metodo(ruta, follow=True)
            assert respuesta.status_code in (403, 404), (nombre, ruta, respuesta.status_code)
    assert probadas >= 3


def test_un_administrador_recibe_404_en_el_portal(urls, cliente_http_admin):
    for nombre, ruta, _ in urls:
        if nombre.startswith("portal:"):
            assert cliente_http_admin.get(ruta).status_code == 404, nombre


def test_ninguna_vista_esta_exenta_de_csrf(urls):
    """SEG-03 y R5: ningún endpoint queda exento."""
    for nombre, ruta, vista in urls:
        assert not getattr(vista, "csrf_exempt", False), (nombre, ruta)


def test_un_formulario_sin_token_csrf_responde_403(cliente_a_activo, administrador_activo, totp):
    from django_otp import DEVICE_ID_SESSION_KEY

    cliente = Client(enforce_csrf_checks=True)
    for ruta, datos in (
        ("/acceso/", {"rut": RUT_CLIENTE_A, "contrasena": "x"}),
        ("/recuperar/", {"rut": RUT_CLIENTE_A}),
        ("/salir/", {}),
        ("/activar/un-token-cualquiera/", {"new_password1": "x", "new_password2": "x"}),
    ):
        respuesta = cliente.post(ruta, datos)
        assert respuesta.status_code == 403, ruta
        assert "No pudimos procesar el formulario" in respuesta.content.decode(), ruta

    # También con sesión: tener la cookie de sesión no reemplaza al token.
    cliente.force_login(cliente_a_activo)
    assert cliente.post("/cuenta/", {"old_password": "x"}).status_code == 403
    assert cliente.post("/salir/").status_code == 403
    assert cliente.get("/portal/").status_code == 200

    admin = Client(enforce_csrf_checks=True)
    admin.force_login(administrador_activo)
    sesion = admin.session
    sesion[DEVICE_ID_SESSION_KEY] = totp.persistent_id
    sesion.save()
    url = f"/panel/usuarios/{cliente_a_activo.uuid}/desbloquear/"
    assert admin.post(url).status_code == 403
    # Con el token en el encabezado, como lo envía HTMX, la petición pasa.
    token = admin.get("/panel/").cookies["csrftoken"].value
    assert admin.post(url, HTTP_X_CSRFTOKEN=token).status_code == 302


def test_las_plantillas_envian_el_token_csrf_en_el_encabezado_para_htmx(client):
    contenido = client.get("/acceso/").content.decode()
    assert 'hx-headers=\'{"X-CSRFToken": "' in contenido
