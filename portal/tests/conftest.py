"""Piezas comunes de las pruebas del portal."""

import datetime
import re

import pytest
from django.test import Client
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import Accion
from conftest import RUT_CLIENTE_A, entrar
from documentos import almacenamiento
from portal import views

ENTREGAS = (Accion.DOCUMENTO_VISTO, Accion.DOCUMENTO_DESCARGADO)


@pytest.fixture
def portal_a(cliente_a_activo):
    """Cliente HTTP con la sesión del cliente de la empresa A."""
    cliente = Client()
    entrar(cliente, RUT_CLIENTE_A)
    return cliente


@pytest.fixture
def espia(monkeypatch):
    """Registra cada intento de leer del almacenamiento para entregar un archivo."""
    llamadas = []
    original = almacenamiento.entregar

    def entregar(clave, **opciones):
        llamadas.append(clave)
        return original(clave, **opciones)

    monkeypatch.setattr(almacenamiento, "entregar", entregar)
    return llamadas


@pytest.fixture
def avanzar_el_reloj(monkeypatch):
    """Mueve el reloj con el que el portal decide la etiqueta "Nuevo"."""

    def avanzar(**delta):
        real = timezone.now

        class Reloj:
            now = staticmethod(lambda: real() + datetime.timedelta(**delta))

        monkeypatch.setattr(views, "timezone", Reloj)

    return avanzar


def pagina(respuesta):
    """El cuerpo sin el token CSRF, que cambia en cada respuesta."""
    return re.sub(rb'"X-CSRFToken": "[^"]+"', b"", respuesta.content)


def enlaces(respuesta):
    """Todos los destinos enlazados desde la página."""
    return re.findall(r'href="([^"]+)"', respuesta.content.decode())


def entregas():
    return EventoAuditoria.objects.filter(accion__in=ENTREGAS).count()


def hoy():
    return timezone.localdate().strftime("%d-%m-%Y")


def cuerpo(respuesta):
    return b"".join(respuesta.streaming_content)
