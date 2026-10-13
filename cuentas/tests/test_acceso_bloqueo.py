"""Bloqueo por intentos fallidos a través de las vistas (AUT-04; prueba 6 de la sección 12.2)."""

import pytest
from django.contrib.auth import SESSION_KEY

from auditoria.models import EventoAuditoria
from auditoria.services import Accion
from conftest import CLAVE, RUT_CLIENTE_A, RUT_INEXISTENTE, entrar

pytestmark = pytest.mark.django_db

MENSAJE_CREDENCIALES = "RUT o contraseña incorrectos."
MENSAJE_BLOQUEO = "Demasiados intentos. Espere unos minutos e intente nuevamente."


def _fallar(client, rut, veces, **extra):
    return [entrar(client, rut, "clave-equivocada-123", **extra) for _ in range(veces)]


def test_el_bloqueo_se_activa_y_rechaza_incluso_la_contrasena_correcta(
    client, cliente_a_activo, settings
):
    settings.ACCESO_INTENTOS_MAXIMOS = 5
    for respuesta in _fallar(client, RUT_CLIENTE_A, 5):
        assert MENSAJE_CREDENCIALES in respuesta.content.decode()

    respuesta = entrar(client, RUT_CLIENTE_A, CLAVE)
    assert respuesta.status_code == 200
    contenido = respuesta.content.decode()
    assert MENSAJE_BLOQUEO in contenido
    assert MENSAJE_CREDENCIALES not in contenido
    assert SESSION_KEY not in client.session

    bloqueo = EventoAuditoria.objects.get(accion=Accion.BLOQUEO)
    assert bloqueo.rut_intentado == "111111111"
    assert bloqueo.empresa == cliente_a_activo.empresa
    assert bloqueo.detalle == "Por RUT e IP"
    # Los intentos durante el bloqueo no suman eventos ni bloqueos nuevos.
    assert EventoAuditoria.objects.filter(accion=Accion.ACCESO_FALLIDO).count() == 5


def test_un_rut_inexistente_se_bloquea_igual_y_con_el_mismo_mensaje(
    client, cliente_a_activo, settings
):
    settings.ACCESO_INTENTOS_MAXIMOS = 3
    _fallar(client, RUT_INEXISTENTE, 3)
    inexistente = entrar(client, RUT_INEXISTENTE, CLAVE).content.decode()
    _fallar(client, RUT_CLIENTE_A, 3)
    existente = entrar(client, RUT_CLIENTE_A, CLAVE).content.decode()
    assert MENSAJE_BLOQUEO in inexistente and MENSAJE_BLOQUEO in existente
    assert EventoAuditoria.objects.filter(accion=Accion.BLOQUEO).count() == 2


def _url_desbloquear(usuario, empresa=None):
    empresa_id = empresa.pk if empresa else usuario.empresa_id
    return f"/panel/clientes/{empresa_id}/usuarios/{usuario.uuid}/desbloquear/"


def test_el_administrador_desbloquea_con_el_boton_de_la_lista_de_usuarios(
    client, cliente_http_admin, cliente_a_activo, settings
):
    """Prueba 6 de la sección 12.2, por el camino real: la lista muestra el bloqueo y su botón."""
    from django.test import Client

    settings.ACCESO_INTENTOS_MAXIMOS = 3
    usuarios = f"/panel/clientes/{cliente_a_activo.empresa_id}/usuarios/"
    url = _url_desbloquear(cliente_a_activo)
    # Sin bloqueo, la lista no ofrece desbloquear.
    contenido = cliente_http_admin.get(usuarios).content.decode()
    assert "Bloqueado" not in contenido and f'action="{url}"' not in contenido

    visitante = Client()
    _fallar(visitante, RUT_CLIENTE_A, 3)
    assert MENSAJE_BLOQUEO in entrar(visitante, RUT_CLIENTE_A).content.decode()

    contenido = cliente_http_admin.get(usuarios).content.decode()
    assert "Bloqueado" in contenido and "Por intentos fallidos" in contenido
    assert f'<form method="post" action="{url}">' in contenido
    assert "Desbloquear" in contenido

    respuesta = cliente_http_admin.post(url, follow=True)
    assert respuesta.redirect_chain == [(usuarios, 302)]
    contenido = respuesta.content.decode()
    assert "Se desbloqueó el acceso de Cliente de A." in contenido
    assert "Bloqueado" not in contenido and f'action="{url}"' not in contenido

    desbloqueo = EventoAuditoria.objects.get(accion=Accion.DESBLOQUEO)
    assert desbloqueo.actor.es_administrador
    assert desbloqueo.objeto_uuid == cliente_a_activo.uuid
    assert desbloqueo.empresa == cliente_a_activo.empresa

    respuesta = entrar(visitante, RUT_CLIENTE_A)
    assert respuesta.status_code == 302 and respuesta["Location"] == "/portal/"


def test_solo_un_administrador_verificado_puede_desbloquear(
    client, cliente_a_activo, cliente_b_activo, administrador_activo, totp
):
    url = _url_desbloquear(cliente_a_activo)
    # Anónimo: al acceso.
    assert client.post(url)["Location"] == f"/acceso/?next={url}"
    # Cliente: 404, aunque el UUID sea correcto.
    entrar(client, cliente_b_activo.rut)
    assert client.post(url).status_code == 404
    client.post("/salir/")
    # Administrador con contraseña pero sin segundo factor: a la verificación.
    entrar(client, administrador_activo.rut)
    assert client.post(url)["Location"] == f"/acceso/verificacion/?next={url}"
    assert not EventoAuditoria.objects.filter(accion=Accion.DESBLOQUEO).exists()


def test_el_desbloqueo_exige_post_y_un_usuario_de_esa_empresa(
    cliente_http_admin, cliente_a_activo, cliente_b_activo, administrador_activo
):
    url = _url_desbloquear(cliente_a_activo)
    assert cliente_http_admin.get(url).status_code == 405
    base = f"/panel/clientes/{cliente_a_activo.empresa_id}/usuarios"
    inexistente = f"{base}/00000000-0000-4000-8000-000000000000/desbloquear/"
    assert cliente_http_admin.post(inexistente).status_code == 404
    # El ID entero no sirve como identificador en la URL.
    assert cliente_http_admin.post(f"{base}/{cliente_a_activo.pk}/desbloquear/").status_code == 404
    # Un usuario solo se alcanza bajo su propia empresa.
    ajena = _url_desbloquear(cliente_a_activo, empresa=cliente_b_activo.empresa)
    assert cliente_http_admin.post(ajena).status_code == 404
    # Un administrador no es usuario de ninguna empresa: se desbloquea con el comando.
    assert (
        cliente_http_admin.post(f"{base}/{administrador_activo.uuid}/desbloquear/").status_code
        == 404
    )
    assert not EventoAuditoria.objects.filter(accion=Accion.DESBLOQUEO).exists()


def test_cambiar_x_forwarded_for_no_evita_el_bloqueo(client, cliente_a_activo, settings):
    """Sin proxy de confianza, el encabezado no se lee: todo cuenta para la IP de la conexión."""
    settings.ACCESO_INTENTOS_MAXIMOS = 3
    settings.PROXY_CONFIANZA_REDES = []
    for numero in range(3):
        entrar(
            client,
            RUT_CLIENTE_A,
            "clave-equivocada-123",
            HTTP_X_FORWARDED_FOR=f"198.51.100.{numero}",
        )
    respuesta = entrar(client, RUT_CLIENTE_A, CLAVE, HTTP_X_FORWARDED_FOR="198.51.100.99")
    assert MENSAJE_BLOQUEO in respuesta.content.decode()
    assert set(EventoAuditoria.objects.values_list("ip", flat=True)) == {"127.0.0.1"}


def test_con_proxy_de_confianza_el_bloqueo_sigue_a_la_ip_real(client, cliente_a_activo, settings):
    settings.ACCESO_INTENTOS_MAXIMOS = 3
    settings.PROXY_CONFIANZA_REDES = ["127.0.0.0/8"]
    # El cliente agrega una dirección falsa distinta cada vez; el proxy añade la real al final.
    for numero in range(3):
        entrar(
            client,
            RUT_CLIENTE_A,
            "clave-equivocada-123",
            HTTP_X_FORWARDED_FOR=f"10.9.9.{numero}, 203.0.113.7",
        )
    bloqueado = entrar(client, RUT_CLIENTE_A, CLAVE, HTTP_X_FORWARDED_FOR="1.1.1.1, 203.0.113.7")
    assert MENSAJE_BLOQUEO in bloqueado.content.decode()
    # Otra persona, desde otra IP real, no queda bloqueada.
    otro = entrar(client, RUT_CLIENTE_A, CLAVE, HTTP_X_FORWARDED_FOR="203.0.113.99")
    assert otro.status_code == 302


def test_limite_por_ip_con_distintos_rut(client, cliente_a_activo, settings):
    settings.ACCESO_INTENTOS_MAXIMOS = 5
    settings.ACCESO_INTENTOS_MAXIMOS_IP = 4
    for cuerpo in ("1-9", "2-7", "3-5", "4-3"):
        entrar(client, cuerpo, "clave-equivocada-123")
    respuesta = entrar(client, RUT_CLIENTE_A, CLAVE)
    assert MENSAJE_BLOQUEO in respuesta.content.decode()
    assert EventoAuditoria.objects.get(accion=Accion.BLOQUEO).detalle == "Por IP"


def test_en_produccion_la_auditoria_anota_la_ip_del_visitante_solo_si_viene_del_tunel(
    client, cliente_a_activo, settings
):
    """AUT-04, con la configuración del servidor: solo el contenedor de cloudflared es de
    confianza y la IP del visitante llega en CF-Connecting-IP."""
    settings.PROXY_CONFIANZA_REDES = ["172.30.57.2/32"]
    settings.PROXY_CONFIANZA_ENCABEZADO = "CF-Connecting-IP"

    def ip_del_ultimo_fallo(**extra):
        entrar(client, RUT_CLIENTE_A, "clave-equivocada-123", **extra)
        return EventoAuditoria.objects.filter(accion=Accion.ACCESO_FALLIDO).latest("pk").ip

    # Por el túnel: la IP que escribió Cloudflare, también en IPv6.
    assert (
        ip_del_ultimo_fallo(REMOTE_ADDR="172.30.57.2", HTTP_CF_CONNECTING_IP="203.0.113.7")
        == "203.0.113.7"
    )
    assert (
        ip_del_ultimo_fallo(REMOTE_ADDR="172.30.57.2", HTTP_CF_CONNECTING_IP="2001:db8::7")
        == "2001:db8::7"
    )
    # Desde otro contenedor de la red, o desde la propia máquina, el encabezado no se cree.
    for origen in ("172.30.57.9", "127.0.0.1"):
        assert (
            ip_del_ultimo_fallo(
                REMOTE_ADDR=origen,
                HTTP_CF_CONNECTING_IP="1.2.3.4",
                HTTP_X_FORWARDED_FOR="1.2.3.4",
            )
            == origen
        )
    # Lo que el visitante escriba en X-Forwarded-For tampoco cuenta, ni por el túnel.
    assert (
        ip_del_ultimo_fallo(
            REMOTE_ADDR="172.30.57.2",
            HTTP_CF_CONNECTING_IP="203.0.113.8",
            HTTP_X_FORWARDED_FOR="1.2.3.4",
        )
        == "203.0.113.8"
    )
