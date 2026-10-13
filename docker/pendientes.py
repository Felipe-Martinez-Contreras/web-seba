"""Dice si una tarea programada tiene trabajo, sin cargar Django.

`reintentar_notificaciones` corre cada 15 minutos y `depurar_solicitudes` a diario, y casi
nunca tienen trabajo. Cargar la aplicación entera para saberlo ocupa memoria y disco en una
máquina que tiene poco de ambos: esta consulta lo averigua con una sola conexión a la base.

Uso: python docker/pendientes.py [tarea]. Sin tarea, `reintentar_notificaciones`.
Termina con 0 si hay trabajo y con 3 si no hay. Cualquier otro código es un error: quien
llama ejecuta la tarea completa de todos modos.

Cada consulta repite la de la aplicación (`SolicitudQuerySet.por_reintentar`, suponiendo que
el correo está configurado, y `SolicitudQuerySet.vencidas`); una prueba compara cada par. Si
sobra una fila, la tarea completa decide. Los límites de la configuración (como el mínimo del
plazo de conservación) los comprueba la tarea completa, no este guion.
"""

import os
import sys

CONSULTA = """
    SELECT count(*) FROM solicitudes_solicitud
    WHERE (notificacion = 'fallida' AND notificacion_intentos < %(maximo)s)
       OR (notificacion = 'pendiente' AND creado_en < now() - interval '5 minutes')
       OR notificacion = 'no_configurada'
"""
CONSULTA_VENCIDAS = """
    SELECT count(*) FROM solicitudes_solicitud
    WHERE creado_en < now() - make_interval(days => %(dias)s)
"""
SIN_PENDIENTES = 3


def maximo_de_intentos():
    return int(os.environ.get("NOTIFICACIONES_INTENTOS_MAXIMOS") or 5)


def dias_de_retencion():
    return int(os.environ.get("SOLICITUDES_RETENCION_DIAS") or 365)


# Por tarea: el texto que se imprime, la consulta y sus parámetros.
TAREAS = {
    "reintentar_notificaciones": (
        "Notificaciones por reintentar",
        CONSULTA,
        lambda: {"maximo": maximo_de_intentos()},
    ),
    "depurar_solicitudes": (
        "Solicitudes vencidas",
        CONSULTA_VENCIDAS,
        lambda: {"dias": dias_de_retencion()},
    ),
}

if __name__ == "__main__":
    import psycopg

    texto, consulta, parametros = TAREAS[sys.argv[1] if len(sys.argv) > 1 else next(iter(TAREAS))]
    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=10) as conexion:
        (cuantas,) = conexion.execute(consulta, parametros()).fetchone()
    print(f"{texto}: {cuantas}")
    sys.exit(0 if cuantas else SIN_PENDIENTES)
