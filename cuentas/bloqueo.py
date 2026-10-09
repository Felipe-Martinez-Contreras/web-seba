"""Bloqueo temporal por intentos fallidos de acceso (AUT-04).

Dos límites: por combinación de RUT e IP, y por IP sola. Se cuenta igual si el RUT
corresponde o no a una cuenta, de modo que el bloqueo no revela su existencia.
"""

from django.conf import settings
from django.core.cache import cache

from core import limites

MOTIVO_RUT_IP = "rut_ip"
MOTIVO_IP = "ip"

# La generación de un RUT forma parte de sus claves: subirla anula de una vez todos sus
# contadores y bloqueos, sin necesidad de conocer desde qué IP se produjeron.
_UN_ANO = 365 * 24 * 3600


def _generacion(rut):
    return cache.get(f"acceso:gen:{rut}", 0)


def _clave_rut_ip(tipo, rut, ip):
    return f"acceso:{tipo}:{_generacion(rut)}:{rut}:{ip}"


def _clave_rut(rut):
    return f"acceso:rut:{_generacion(rut)}:{rut}"


def esta_bloqueado(rut, ip):
    """Indica si este intento debe rechazarse sin evaluar la contraseña."""
    if cache.get(f"acceso:bloqueo-ip:{ip}"):
        return True
    return bool(rut and cache.get(_clave_rut_ip("bloqueo", rut, ip)))


def registrar_fallo(rut, ip):
    """Cuenta un intento fallido. Devuelve el motivo si con él se activa un bloqueo."""
    ventana = settings.ACCESO_VENTANA_MINUTOS * 60
    duracion = settings.ACCESO_BLOQUEO_MINUTOS * 60
    motivo = None
    if rut and limites.contar(_clave_rut_ip("fallos", rut, ip), ventana) >= (
        settings.ACCESO_INTENTOS_MAXIMOS
    ):
        cache.set(_clave_rut_ip("bloqueo", rut, ip), True, timeout=duracion)
        cache.set(_clave_rut(rut), True, timeout=duracion)
        limites.reiniciar(_clave_rut_ip("fallos", rut, ip))
        motivo = MOTIVO_RUT_IP
    if limites.contar(f"acceso:fallos-ip:{ip}", ventana) >= settings.ACCESO_INTENTOS_MAXIMOS_IP:
        cache.set(f"acceso:bloqueo-ip:{ip}", True, timeout=duracion)
        limites.reiniciar(f"acceso:fallos-ip:{ip}")
        motivo = motivo or MOTIVO_IP
    return motivo


def limpiar(rut, ip):
    """Tras un acceso correcto, los fallos anteriores de ese RUT desde esa IP dejan de contar."""
    limites.reiniciar(_clave_rut_ip("fallos", rut, ip))


def rut_bloqueado(rut):
    """Indica si el RUT tiene algún bloqueo vigente, desde cualquier IP."""
    return bool(cache.get(_clave_rut(rut)))


def desbloquear_rut(rut):
    cache.set(f"acceso:gen:{rut}", _generacion(rut) + 1, timeout=_UN_ANO)


def desbloquear_ip(ip):
    cache.delete(f"acceso:bloqueo-ip:{ip}")
    limites.reiniciar(f"acceso:fallos-ip:{ip}")
