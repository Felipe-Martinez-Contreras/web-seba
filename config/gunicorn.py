"""Configuración de Gunicorn para producción: `gunicorn -c config/gunicorn.py config.wsgi`.

Pensada para una máquina con 1 GB de memoria detrás de un proxy (docs/DESPLIEGUE.md).
"""

import os

# Siempre TCP, nunca un socket Unix: sin una dirección en la conexión la aplicación no
# distingue al proxy de confianza y todos los clientes compartirían los límites por IP.
bind = "0.0.0.0:8000"

# Hilos: una subida lenta de 25 MB ocupa un hilo y no un proceso entero.
worker_class = "gthread"
workers = int(os.environ.get("GUNICORN_PROCESOS", "2"))
threads = int(os.environ.get("GUNICORN_HILOS", "2"))
# La aplicación se carga una vez, antes de crear los procesos: en una máquina chica, que cada
# proceso importara Django por su cuenta alargaba el arranque. Nada abre conexiones al importar.
preload_app = True
# Con hilos, este plazo es el del latido del proceso, no el de cada petición.
timeout = 120
graceful_timeout = 30
keepalive = 5
# Cada proceso se renueva cada cierto número de peticiones: la memoria no crece sin tope.
max_requests = 500
max_requests_jitter = 50
# El latido se escribe en memoria; en el disco del contenedor puede frenar al proceso.
worker_tmp_dir = "/dev/shm"

# Logs en JSON y por stdout, con el mismo formateador de la aplicación: oculta el token de
# los enlaces de activación y de restablecimiento (SEG-10). El de acceso anota la ruta sin
# la cadena de consulta (lleva textos de búsqueda) y sin la IP del visitante.
accesslog = "-"
access_log_format = "%(m)s %(U)s %(s)s %(B)s bytes %(M)s ms"
logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "core.logs.FormatoJson"}},
    "handlers": {
        "consola": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "json",
        }
    },
    "root": {"level": "INFO", "handlers": ["consola"]},
    "loggers": {
        "gunicorn.error": {"level": "INFO", "handlers": ["consola"], "propagate": False},
        "gunicorn.access": {"level": "INFO", "handlers": ["consola"], "propagate": False},
    },
}
