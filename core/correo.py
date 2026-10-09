"""Envío de correo con resultado explícito (R4): nunca se da por enviado lo que falló."""

import logging

from django.conf import settings
from django.core import mail
from django.db import models

logger = logging.getLogger(__name__)


class Resultado(models.TextChoices):
    ENVIADA = "enviada", "Enviada"
    FALLIDA = "fallida", "Fallida"
    NO_CONFIGURADA = "no_configurada", "Correo no configurado"


def correo_configurado():
    return "default" in mail.mailers and bool(settings.DEFAULT_FROM_EMAIL)


def enviar(asunto, cuerpo, destinatarios, *, reply_to=None):
    """Envía un correo de texto. Devuelve (Resultado, error resumido).

    El error resumido es solo el tipo de la excepción: el mensaje completo va al log,
    que no incluye el cuerpo del correo (SEG-10).
    """
    if not correo_configurado():
        return Resultado.NO_CONFIGURADA, ""
    mensaje = mail.EmailMessage(
        subject=asunto,
        body=cuerpo,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=list(destinatarios),
        reply_to=reply_to,
    )
    try:
        enviados = mail.mailers.default.send_messages([mensaje])
    except Exception as error:
        logger.exception("No se pudo enviar un correo")
        return Resultado.FALLIDA, type(error).__name__
    if not enviados:
        return Resultado.FALLIDA, "El servidor no aceptó el mensaje"
    return Resultado.ENVIADA, ""
