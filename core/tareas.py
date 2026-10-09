"""Trabajo fuera de la petición, sin colas ni servicios adicionales (sección 5).

Se usa para lo que no debe alargar la respuesta ni delatar con su duración qué ocurrió,
como hablar con el servidor de correo. Limitación: si el proceso se reinicia mientras el
hilo trabaja, esa tarea se pierde (docs/SEGURIDAD.md).
"""

import logging
import threading

from django.conf import settings
from django.db import connections

logger = logging.getLogger(__name__)


def _ejecutar_en_hilo(funcion, argumentos):
    try:
        funcion(*argumentos)
    except Exception:
        logger.exception("Falló una tarea en segundo plano: %s", funcion.__name__)
    finally:
        # Cada hilo abre su propia conexión a la base de datos: hay que cerrarla.
        connections.close_all()


def en_segundo_plano(funcion, *argumentos):
    """Ejecuta la función en un hilo aparte y lo devuelve.

    En las pruebas (TAREAS_SINCRONAS) se ejecuta de inmediato, en el mismo hilo.
    """
    if settings.TAREAS_SINCRONAS:
        funcion(*argumentos)
        return None
    hilo = threading.Thread(target=_ejecutar_en_hilo, args=(funcion, argumentos))
    hilo.start()
    return hilo
