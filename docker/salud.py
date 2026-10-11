"""Comprueba, desde dentro del contenedor de producción, que la aplicación responde.

Habla con Gunicorn como lo hace el proxy: con el nombre del sitio y avisando que la petición
llegó por HTTPS. Sin eso la aplicación rechaza el nombre o redirige a HTTPS.
Uso: python docker/salud.py [ruta]. Termina con código 1 si la respuesta no es 200.
"""

import os
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit

ruta = sys.argv[1] if len(sys.argv) > 1 else "/salud/"
peticion = urllib.request.Request(
    f"http://127.0.0.1:8000{ruta}",
    headers={
        "Host": urlsplit(os.environ["SITIO_URL"]).netloc,
        os.environ.get("PROXY_HTTPS_ENCABEZADO") or "X-Forwarded-Proto": "https",
    },
)
try:
    with urllib.request.urlopen(peticion, timeout=5) as respuesta:
        print(respuesta.status, respuesta.read(200).decode("utf-8", "replace"))
except urllib.error.HTTPError as error:
    sys.exit(f"Respondió {error.code}")
except OSError as error:
    sys.exit(f"Sin respuesta: {error}")
