"""Antispam de los formularios públicos, sin servicios externos (SOL-04).

Tres controles: un campo trampa que las personas no ven, un tiempo mínimo entre mostrar el
formulario y enviarlo, y un máximo de envíos por hora desde una misma IP. Lo descartado no
se guarda ni se notifica, y quien lo envió no recibe el motivo.
"""

import enum
import logging
import time

from django.conf import settings
from django.core import signing
from django.utils.module_loading import import_string

from core import limites

logger = logging.getLogger(__name__)

# Nombre neutro: un robot que rellena todo lo que encuentra también rellena este.
CAMPO_TRAMPA = "sitio_web"
CAMPO_MARCA = "marca"
# Un formulario abierto por más tiempo que este debe enviarse de nuevo.
MARCA_VIGENCIA_SEGUNDOS = 24 * 3600
_UNA_HORA = 3600
_firmante = signing.Signer(salt="solicitudes.antispam.marca")


class Motivo(enum.StrEnum):
    TRAMPA = "campo trampa"
    MARCA = "marca de tiempo ausente o alterada"
    TIEMPO = "enviado demasiado rápido"
    VENCIDA = "formulario abierto demasiado tiempo"
    CAPTCHA = "captcha"
    LIMITE = "límite de envíos por IP"


def _ahora():
    return time.time()


def nueva_marca():
    """Marca de tiempo firmada, para el campo oculto del formulario."""
    return _firmante.sign(str(int(_ahora())))


def _edad(marca):
    """Segundos desde que se emitió la marca, o None si falta o la firma no coincide."""
    try:
        return _ahora() - int(_firmante.unsign(marca or ""))
    except (signing.BadSignature, ValueError):
        return None


def marca_para_reintento(request):
    """La marca que lleva el formulario al mostrarlo de nuevo con errores: la misma, si
    sigue vigente, para no castigar con otra espera a quien corrige un campo."""
    marca = request.POST.get(CAMPO_MARCA, "")
    edad = _edad(marca)
    if edad is not None and 0 <= edad <= MARCA_VIGENCIA_SEGUNDOS:
        return marca
    return nueva_marca()


def _captcha_rechaza(request):
    """Punto de extensión, desactivado por defecto. `SOLICITUDES_CAPTCHA` es la ruta de una
    función que recibe la petición y devuelve si el captcha fue resuelto."""
    if not settings.SOLICITUDES_CAPTCHA:
        return False
    return not import_string(settings.SOLICITUDES_CAPTCHA)(request)


def revisar(request):
    """Revisa un envío ya validado. Devuelve el motivo del descarte, o None si pasa.

    El límite por IP se cuenta al final: solo consumen cupo los envíos que se iban a guardar.
    """
    motivo = _revisar(request)
    if motivo:
        # Sin datos del visitante: solo qué control actuó.
        logger.info("Solicitud descartada por el antispam: %s", motivo.value)
    return motivo


def _revisar(request):
    if request.POST.get(CAMPO_TRAMPA, "").strip():
        return Motivo.TRAMPA
    edad = _edad(request.POST.get(CAMPO_MARCA))
    if edad is None or edad < 0:
        return Motivo.MARCA
    if edad < settings.SOLICITUDES_TIEMPO_MINIMO_SEGUNDOS:
        return Motivo.TIEMPO
    if edad > MARCA_VIGENCIA_SEGUNDOS:
        return Motivo.VENCIDA
    if _captcha_rechaza(request):
        return Motivo.CAPTCHA
    envios = limites.contar(f"solicitudes:ip:{request.ip_cliente}", _UNA_HORA)
    if envios > settings.SOLICITUDES_MAXIMO_POR_HORA_IP:
        return Motivo.LIMITE
    return None
