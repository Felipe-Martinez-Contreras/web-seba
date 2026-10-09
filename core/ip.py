"""IP real del cliente (AUT-04).

El encabezado del proxy solo se lee cuando la conexión viene de un proxy de confianza
configurado. Un `X-Forwarded-For` enviado por cualquier otro origen se ignora.
"""

import ipaddress
from functools import lru_cache

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def interpretar_redes(valores):
    """Convierte una lista de redes CIDR en objetos de red; falla si alguna es inválida."""
    redes = []
    for valor in valores:
        try:
            redes.append(ipaddress.ip_network(valor, strict=False))
        except ValueError:
            raise ImproperlyConfigured(
                f"PROXY_CONFIANZA_REDES contiene una red inválida: {valor!r}."
            ) from None
    return tuple(redes)


@lru_cache(maxsize=8)
def _redes(valores):
    return interpretar_redes(valores)


def _direccion(texto):
    try:
        direccion = ipaddress.ip_address((texto or "").strip())
    except ValueError:
        return None
    # ::ffff:203.0.113.7 y 203.0.113.7 son el mismo cliente.
    return getattr(direccion, "ipv4_mapped", None) or direccion


def _es_de_confianza(direccion, redes):
    return any(direccion.version == red.version and direccion in red for red in redes)


def ip_cliente(request):
    """Devuelve la IP del cliente como texto, o None si no se puede determinar."""
    remota = _direccion(request.META.get("REMOTE_ADDR"))
    if remota is None:
        return None
    redes = _redes(tuple(settings.PROXY_CONFIANZA_REDES))
    if not redes or not _es_de_confianza(remota, redes):
        return str(remota)

    # De derecha a izquierda: cada proxy agrega al final la dirección de quien se le conectó.
    # La primera que no es un proxy de confianza es el cliente; lo que haya más a la
    # izquierda lo pudo escribir el propio cliente y no se usa.
    encabezado = request.headers.get(settings.PROXY_CONFIANZA_ENCABEZADO, "")
    for parte in reversed(encabezado.split(",")):
        direccion = _direccion(parte)
        if direccion is None:
            return str(remota)
        if not _es_de_confianza(direccion, redes):
            return str(direccion)
    return str(remota)
