"""Contadores y bloqueos de acceso, sin pasar por las vistas (AUT-04)."""

import pytest
from django.core.cache import cache

from core import limites
from cuentas import bloqueo

RUT = "111111111"
IP = "203.0.113.7"

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _cache_limpia():
    cache.clear()
    yield
    cache.clear()


def _fallar(veces, rut=RUT, ip=IP):
    return [bloqueo.registrar_fallo(rut, ip) for _ in range(veces)]


def test_el_bloqueo_se_activa_al_llegar_al_maximo_de_intentos(settings):
    settings.ACCESO_INTENTOS_MAXIMOS = 5
    assert _fallar(4) == [None] * 4
    assert bloqueo.esta_bloqueado(RUT, IP) is False
    assert _fallar(1) == [bloqueo.MOTIVO_RUT_IP]
    assert bloqueo.esta_bloqueado(RUT, IP) is True
    assert bloqueo.rut_bloqueado(RUT) is True


def test_el_bloqueo_es_por_combinacion_de_rut_e_ip(settings):
    settings.ACCESO_INTENTOS_MAXIMOS = 3
    _fallar(3)
    assert bloqueo.esta_bloqueado(RUT, "198.51.100.1") is False
    assert bloqueo.esta_bloqueado("222222222", IP) is False


def test_un_acceso_correcto_reinicia_los_fallos(settings):
    settings.ACCESO_INTENTOS_MAXIMOS = 3
    _fallar(2)
    bloqueo.limpiar(RUT, IP)
    assert _fallar(2) == [None, None]
    assert bloqueo.esta_bloqueado(RUT, IP) is False


def test_limite_por_ip_aunque_cambie_el_rut(settings):
    settings.ACCESO_INTENTOS_MAXIMOS = 5
    settings.ACCESO_INTENTOS_MAXIMOS_IP = 4
    motivos = [bloqueo.registrar_fallo(f"{numero}0000000", IP) for numero in range(1, 5)]
    assert motivos == [None, None, None, bloqueo.MOTIVO_IP]
    # Bloquea cualquier RUT desde esa IP, incluso sin RUT válido.
    assert bloqueo.esta_bloqueado("999999999", IP) is True
    assert bloqueo.esta_bloqueado("", IP) is True
    assert bloqueo.esta_bloqueado("999999999", "198.51.100.1") is False


def test_sin_rut_valido_solo_cuenta_para_la_ip(settings):
    settings.ACCESO_INTENTOS_MAXIMOS = 2
    settings.ACCESO_INTENTOS_MAXIMOS_IP = 3
    assert [bloqueo.registrar_fallo("", IP) for _ in range(3)] == [None, None, bloqueo.MOTIVO_IP]


def test_desbloquear_un_rut_anula_sus_bloqueos_desde_cualquier_ip(settings):
    settings.ACCESO_INTENTOS_MAXIMOS = 2
    _fallar(2, ip="203.0.113.7")
    _fallar(2, ip="198.51.100.1")
    _fallar(1, ip="192.0.2.50")
    bloqueo.desbloquear_rut(RUT)
    assert bloqueo.esta_bloqueado(RUT, "203.0.113.7") is False
    assert bloqueo.esta_bloqueado(RUT, "198.51.100.1") is False
    assert bloqueo.rut_bloqueado(RUT) is False
    # Los contadores previos tampoco cuentan: hace falta el máximo completo otra vez.
    assert _fallar(1, ip="192.0.2.50") == [None]


def test_desbloquear_una_ip(settings):
    settings.ACCESO_INTENTOS_MAXIMOS_IP = 2
    bloqueo.registrar_fallo("", IP)
    bloqueo.registrar_fallo("", IP)
    assert bloqueo.esta_bloqueado("", IP) is True
    bloqueo.desbloquear_ip(IP)
    assert bloqueo.esta_bloqueado("", IP) is False


def test_la_ventana_no_se_alarga_con_cada_fallo(monkeypatch):
    reloj = [limites.time.time()]
    monkeypatch.setattr(limites, "_ahora", lambda: reloj[0])
    assert limites.contar("prueba:ventana", 900) == 1
    reloj[0] += 600
    assert limites.contar("prueba:ventana", 900) == 2
    # Pasaron 15 minutos desde el primer evento: la cuenta parte de nuevo.
    reloj[0] += 301
    assert limites.contar("prueba:ventana", 900) == 1


def test_el_bloqueo_no_se_pierde_aunque_la_cache_reciba_cientos_de_entradas(settings):
    """Con el tope por defecto de la caché (300 entradas), al llenarla se borraban primero
    las claves de acceso: bastaban unos cientos de solicitudes de recuperación."""
    settings.ACCESO_INTENTOS_MAXIMOS = 5
    settings.ACCESO_INTENTOS_MAXIMOS_IP = 5
    _fallar(5)
    bloqueo.desbloquear_rut("222222222")
    assert bloqueo.esta_bloqueado(RUT, IP) and bloqueo.rut_bloqueado(RUT)

    for numero in range(400):
        cache.set(f"recuperar:rut:{numero}", {"n": 1, "desde": 0}, timeout=3600)

    assert bloqueo.esta_bloqueado(RUT, IP) and bloqueo.rut_bloqueado(RUT)
    assert cache.get(f"acceso:bloqueo-ip:{IP}") is True
    assert cache.get("acceso:gen:222222222") == 1
