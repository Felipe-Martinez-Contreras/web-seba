"""Contadores con ventana de tiempo sobre la caché en base de datos (sección 5).

No son atómicos: bajo peticiones simultáneas puede colarse algún intento de más.
Para el volumen de este sistema es aceptable (docs/SEGURIDAD.md).
"""

import time

from django.core.cache import cache


def _ahora():
    return time.time()


def contar(clave, ventana):
    """Suma uno al contador y devuelve el total dentro de la ventana (en segundos).

    La ventana parte con el primer evento y no se alarga con los siguientes.
    """
    ahora = _ahora()
    datos = cache.get(clave)
    if not datos or ahora - datos["desde"] >= ventana:
        datos = {"n": 0, "desde": ahora}
    datos["n"] += 1
    cache.set(clave, datos, timeout=max(1, int(ventana - (ahora - datos["desde"]))))
    return datos["n"]


def reiniciar(clave):
    cache.delete(clave)
