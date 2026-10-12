"""Comprueba, desde dentro del contenedor de producción, que la aplicación responde.

Habla con Gunicorn como lo hace el proxy: con el nombre del sitio y avisando que la petición
llegó por HTTPS. Sin eso la aplicación rechaza el nombre o redirige a HTTPS.
Uso: python -I -S docker/salud.py [ruta ...]. Termina con código 1 si alguna no responde 200.
Con varias rutas las pide una tras otra y anota cuánto tardó cada una: así se precalienta la
aplicación después de un despliegue.

Es el healthcheck del contenedor y corre cada minuto en una máquina con poca memoria: solo
usa el socket. Una biblioteca HTTP cargaría decenas de módulos en cada sondeo.
"""

import os
import socket
import sys
import time

PLAZO_SEGUNDOS = 20

rutas = sys.argv[1:] or ["/salud/"]
sitio = os.environ["SITIO_URL"].split("://", 1)[-1].split("/", 1)[0]
encabezado_https = os.environ.get("PROXY_HTTPS_ENCABEZADO") or "X-Forwarded-Proto"


def pedir(ruta):
    """Código de estado y cuerpo de un GET. HTTP/1.0: la respuesta llega sin trozos."""
    peticion = f"GET {ruta} HTTP/1.0\r\nHost: {sitio}\r\n{encabezado_https}: https\r\n\r\n"
    with socket.create_connection(("127.0.0.1", 8000), timeout=PLAZO_SEGUNDOS) as conexion:
        conexion.sendall(peticion.encode())
        respuesta = b""
        while trozo := conexion.recv(65536):
            respuesta += trozo
    cabecera, _, cuerpo = respuesta.partition(b"\r\n\r\n")
    estado = cabecera.split(b"\r\n", 1)[0].split()[1:2]
    return (estado[0].decode("latin-1") if estado else "sin estado"), cuerpo


fallos = 0
for ruta in rutas:
    inicio = time.monotonic()
    try:
        estado, cuerpo = pedir(ruta)
    except OSError as error:
        print(f"Sin respuesta en {ruta}: {error}", file=sys.stderr)
        fallos += 1
        continue
    if estado != "200":
        print(f"Respondió {estado} en {ruta}", file=sys.stderr)
        fallos += 1
    elif len(rutas) == 1:
        print(estado, cuerpo[:200].decode("utf-8", "replace"))
    else:
        print(estado, ruta, f"{(time.monotonic() - inicio) * 1000:.0f} ms")
sys.exit(1 if fallos else 0)
