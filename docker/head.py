"""Comprueba, desde dentro del contenedor de producción, que HEAD responde 200 y sin cuerpo.

Habla con Gunicorn por el socket, sin una biblioteca HTTP: estas descartan por su cuenta el
cuerpo de una respuesta a HEAD y no dejarían ver si el servidor lo envió.
Uso: python docker/head.py [ruta]. Termina con código 1 si no es un 200 sin cuerpo.
"""

import os
import socket
import sys
from urllib.parse import urlsplit

ruta = sys.argv[1] if len(sys.argv) > 1 else "/salud/"
encabezado_https = os.environ.get("PROXY_HTTPS_ENCABEZADO") or "X-Forwarded-Proto"
peticion = (
    f"HEAD {ruta} HTTP/1.1\r\n"
    f"Host: {urlsplit(os.environ['SITIO_URL']).netloc}\r\n"
    f"{encabezado_https}: https\r\n"
    "Connection: close\r\n\r\n"
)
try:
    with socket.create_connection(("127.0.0.1", 8000), timeout=5) as conexion:
        conexion.sendall(peticion.encode())
        respuesta = b""
        while trozo := conexion.recv(65536):
            respuesta += trozo
except OSError as error:
    sys.exit(f"Sin respuesta: {error}")

cabecera, _, cuerpo = respuesta.partition(b"\r\n\r\n")
estado = cabecera.split(b"\r\n", 1)[0].decode("latin-1")
print(estado, f"({len(cuerpo)} bytes de cuerpo)")
if estado.split()[1:2] != ["200"] or cuerpo:
    sys.exit(1)
