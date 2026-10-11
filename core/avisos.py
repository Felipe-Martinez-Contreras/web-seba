"""Aviso por correo al administrador cuando la aplicación responde un error 500 (RNF-05).

No se usa el `AdminEmailHandler` de Django: su correo incluye los datos del formulario
(una contraseña escrita en el acceso) y la ruta completa (el token de un enlace). Este aviso
dice dónde falló y nada más; el detalle queda en el log del servidor (SEG-10).
"""

import logging
import threading
import time
import traceback
from collections import deque
from pathlib import Path
from urllib.parse import urlsplit

from django.conf import settings
from django.utils import timezone

from core.logs import ocultar_tokens

_HORA = 3600
_enviados = deque()
_candado = threading.Lock()


def reiniciar_cupo():
    with _candado:
        _enviados.clear()


def _tomar_cupo():
    """Devuelve cuántos avisos quedan tras este, o None si ya no hay cupo en esta hora.

    El tope es por proceso y vive en memoria: tiene que funcionar también cuando lo que
    falla es la base de datos.
    """
    ahora = time.monotonic()
    with _candado:
        while _enviados and ahora - _enviados[0] > _HORA:
            _enviados.popleft()
        if len(_enviados) >= settings.ERRORES_AVISOS_POR_HORA:
            return None
        _enviados.append(ahora)
        return settings.ERRORES_AVISOS_POR_HORA - len(_enviados)


def nombre_del_sitio():
    return urlsplit(settings.SITIO_URL).hostname or settings.SITIO_URL


def _ruta_del_archivo(archivo):
    try:
        return Path(archivo).resolve().relative_to(settings.BASE_DIR).as_posix()
    except ValueError:
        return archivo


def _donde(record):
    """Tipo de la excepción y sus marcos: archivo, línea y función. Sin el mensaje de la
    excepción, que puede traer datos (por ejemplo, el valor que violó una restricción)."""
    if not record.exc_info or record.exc_info[0] is None:
        return ["Sin excepción asociada."]
    tipo, _, traza = record.exc_info
    lineas = [f"Excepción: {tipo.__name__}", "Dónde:"]
    lineas += [
        f"  {_ruta_del_archivo(marco.filename)}:{marco.lineno} en {marco.name}"
        for marco in traceback.extract_tb(traza)
    ]
    return lineas


def componer(record, restantes):
    request = getattr(record, "request", None)
    peticion = "Petición: desconocida"
    if request is not None and hasattr(request, "path"):
        peticion = f"Petición: {request.method} {ocultar_tokens(request.path)}"
    lineas = [
        f"Sitio: {nombre_del_sitio()}",
        f"Fecha: {timezone.localtime().strftime('%d-%m-%Y %H:%M:%S')}",
        peticion,
        *_donde(record),
        "",
        "El detalle completo está en el log del servidor.",
    ]
    if restantes == 0:
        lineas.append("Se alcanzó el tope de avisos por hora: no habrá más avisos hasta entonces.")
    return f"[{nombre_del_sitio()}] Error 500 en el servidor", "\n".join(lineas)


def _enviar(asunto, cuerpo, destinatarios):
    from core import correo

    correo.enviar(asunto, cuerpo, destinatarios)


class AvisoDeErrorPorCorreo(logging.Handler):
    """Manejador para `django.request`. Sin `ERRORES_DESTINATARIOS` no hace nada."""

    def __init__(self):
        super().__init__(level=logging.ERROR)

    def emit(self, record):
        try:
            destinatarios = settings.ERRORES_DESTINATARIOS
            if not destinatarios:
                return
            restantes = _tomar_cupo()
            if restantes is None:
                return
            asunto, cuerpo = componer(record, restantes)
            from core.tareas import en_segundo_plano

            # Fuera de la petición: el visitante no espera al servidor de correo.
            en_segundo_plano(_enviar, asunto, cuerpo, list(destinatarios))
        except Exception:
            self.handleError(record)
