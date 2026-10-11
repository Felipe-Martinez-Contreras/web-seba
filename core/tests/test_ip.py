import pytest
from django.core.exceptions import ImproperlyConfigured

from core.ip import interpretar_redes, ip_cliente
from core.middleware import IpClienteMiddleware

PROXY = "10.0.0.5"


def _request(rf, remota, encabezado=None, nombre="HTTP_X_FORWARDED_FOR"):
    extra = {"REMOTE_ADDR": remota}
    if encabezado is not None:
        extra[nombre] = encabezado
    return rf.get("/", **extra)


def test_sin_proxies_configurados_no_se_lee_ningun_encabezado(rf, settings):
    settings.PROXY_CONFIANZA_REDES = []
    assert ip_cliente(_request(rf, "198.51.100.9", "203.0.113.7")) == "198.51.100.9"


def test_un_encabezado_enviado_por_un_origen_que_no_es_de_confianza_se_ignora(rf, settings):
    settings.PROXY_CONFIANZA_REDES = ["10.0.0.0/8"]
    assert ip_cliente(_request(rf, "198.51.100.9", "203.0.113.7")) == "198.51.100.9"


def test_desde_el_proxy_de_confianza_se_usa_la_direccion_que_el_agrego(rf, settings):
    settings.PROXY_CONFIANZA_REDES = ["10.0.0.0/8"]
    assert ip_cliente(_request(rf, PROXY, "203.0.113.7")) == "203.0.113.7"


def test_lo_que_el_cliente_escribio_a_la_izquierda_no_se_usa(rf, settings):
    settings.PROXY_CONFIANZA_REDES = ["10.0.0.0/8"]
    # falsa (la escribió el cliente), real (la agregó el primer proxy), proxy intermedio.
    encabezado = "1.2.3.4, 203.0.113.7, 10.0.0.9"
    assert ip_cliente(_request(rf, PROXY, encabezado)) == "203.0.113.7"


@pytest.mark.parametrize("encabezado", ["no-es-una-ip", "203.0.113.7, <script>", "", " , "])
def test_un_encabezado_malformado_vuelve_a_la_direccion_de_la_conexion(rf, settings, encabezado):
    settings.PROXY_CONFIANZA_REDES = ["10.0.0.0/8"]
    assert ip_cliente(_request(rf, PROXY, encabezado)) == PROXY


def test_si_toda_la_cadena_son_proxies_se_usa_la_direccion_de_la_conexion(rf, settings):
    settings.PROXY_CONFIANZA_REDES = ["10.0.0.0/8"]
    assert ip_cliente(_request(rf, PROXY, "10.0.0.7, 10.0.0.8")) == PROXY


def test_sin_encabezado_desde_el_proxy_se_usa_la_direccion_de_la_conexion(rf, settings):
    settings.PROXY_CONFIANZA_REDES = ["10.0.0.0/8"]
    assert ip_cliente(_request(rf, PROXY)) == PROXY


def test_ipv6_y_direcciones_ipv4_mapeadas(rf, settings):
    settings.PROXY_CONFIANZA_REDES = ["fd00::/8", "10.0.0.0/8"]
    assert ip_cliente(_request(rf, "fd00::1", "2001:db8::7")) == "2001:db8::7"
    assert ip_cliente(_request(rf, "::ffff:10.0.0.5", "::ffff:203.0.113.7")) == "203.0.113.7"
    assert ip_cliente(_request(rf, "2001:db8::9", "203.0.113.7")) == "2001:db8::9"


def test_el_encabezado_configurado_es_el_unico_que_se_lee(rf, settings):
    settings.PROXY_CONFIANZA_REDES = ["10.0.0.0/8"]
    settings.PROXY_CONFIANZA_ENCABEZADO = "X-Real-IP"
    assert ip_cliente(_request(rf, PROXY, "203.0.113.7")) == PROXY
    assert ip_cliente(_request(rf, PROXY, "203.0.113.7", nombre="HTTP_X_REAL_IP")) == "203.0.113.7"


def test_detras_de_cloudflared_la_ip_sale_de_cf_connecting_ip(rf, settings):
    """Producción: solo el contenedor del túnel es de confianza y Cloudflare escribe la IP
    del visitante, una sola, en CF-Connecting-IP."""
    settings.PROXY_CONFIANZA_REDES = ["172.30.57.2/32"]
    settings.PROXY_CONFIANZA_ENCABEZADO = "CF-Connecting-IP"
    cf = "HTTP_CF_CONNECTING_IP"
    assert ip_cliente(_request(rf, "172.30.57.2", "203.0.113.7", nombre=cf)) == "203.0.113.7"
    assert ip_cliente(_request(rf, "172.30.57.2", "2001:db8::7", nombre=cf)) == "2001:db8::7"
    # X-Forwarded-For lo puede traer escrito el visitante: no se lee.
    assert ip_cliente(_request(rf, "172.30.57.2", "1.2.3.4")) == "172.30.57.2"
    # Otro contenedor de la misma red de Docker no es el túnel: su encabezado no cuenta.
    assert ip_cliente(_request(rf, "172.30.57.9", "203.0.113.7", nombre=cf)) == "172.30.57.9"


def test_sin_direccion_de_conexion_no_hay_ip(rf):
    assert ip_cliente(_request(rf, "")) is None


def test_una_red_invalida_impide_arrancar():
    with pytest.raises(ImproperlyConfigured, match="PROXY_CONFIANZA_REDES"):
        interpretar_redes(["10.0.0.0/8", "no-es-una-red"])


def test_el_middleware_deja_la_ip_en_la_peticion(rf, settings):
    settings.PROXY_CONFIANZA_REDES = ["10.0.0.0/8"]
    vistas = []
    IpClienteMiddleware(vistas.append)(_request(rf, PROXY, "203.0.113.7"))
    assert vistas[0].ip_cliente == "203.0.113.7"
