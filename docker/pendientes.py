"""Dice si hay notificaciones de solicitudes por reintentar, sin cargar Django.

La tarea `reintentar_notificaciones` corre cada 15 minutos y casi nunca tiene trabajo. Cargar
la aplicación entera para saberlo ocupa memoria y disco en una máquina que tiene poco de
ambos: esta consulta lo averigua con una sola conexión a la base.

Uso: python docker/pendientes.py. Termina con 0 si hay alguna y con 3 si no hay ninguna.
Cualquier otro código es un error: quien llama ejecuta la tarea completa de todos modos.

La consulta repite la de `SolicitudQuerySet.por_reintentar` suponiendo que el correo está
configurado; una prueba compara ambas. Si sobra una, la tarea completa decide.
"""

import os
import sys

CONSULTA = """
    SELECT count(*) FROM solicitudes_solicitud
    WHERE (notificacion = 'fallida' AND notificacion_intentos < %(maximo)s)
       OR (notificacion = 'pendiente' AND creado_en < now() - interval '5 minutes')
       OR notificacion = 'no_configurada'
"""
SIN_PENDIENTES = 3


def maximo_de_intentos():
    return int(os.environ.get("NOTIFICACIONES_INTENTOS_MAXIMOS") or 5)


if __name__ == "__main__":
    import psycopg

    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=10) as conexion:
        (cuantas,) = conexion.execute(CONSULTA, {"maximo": maximo_de_intentos()}).fetchone()
    print(f"Notificaciones por reintentar: {cuantas}")
    sys.exit(0 if cuantas else SIN_PENDIENTES)
