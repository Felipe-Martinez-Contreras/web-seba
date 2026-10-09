"""Trabajo fuera de la petición, sin colas ni servicios adicionales (sección 5).

Se usa para lo que no debe alargar la respuesta ni delatar con su duración qué ocurrió,
como hablar con el servidor de correo. Limitación: si el proceso se reinicia mientras la
tarea espera o trabaja, esa tarea se pierde (docs/SEGURIDAD.md).
"""

import logging
import random
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
    """Ejecuta la función en un hilo aparte, un poco después, y devuelve ese hilo.

    El hilo no parte de inmediato: si lo hiciera, competiría por la CPU con la petición
    que lo lanzó y la respuesta tardaría más justo cuando hay trabajo que hacer. La espera
    tiene además una parte al azar, para que el trabajo no caiga a un tiempo fijo.

    En las pruebas (TAREAS_SINCRONAS) se ejecuta de inmediato, en el mismo hilo.
    """
    if settings.TAREAS_SINCRONAS:
        funcion(*argumentos)
        return None
    espera = settings.TAREAS_ESPERA_SEGUNDOS
    hilo = threading.Timer(
        espera + random.uniform(0, espera), _ejecutar_en_hilo, args=(funcion, argumentos)
    )
    hilo.start()
    return hilo
