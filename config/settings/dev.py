"""Desarrollo local."""

from .base import *  # noqa: F403
from .base import env

DEBUG = True
ALLOWED_HOSTS = env.lista("ALLOWED_HOSTS", ["localhost", "127.0.0.1"])

# Sin servidor SMTP configurado, los correos se imprimen en la consola del contenedor.
if not MAILERS:  # noqa: F405
    MAILERS = {"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}
    DEFAULT_FROM_EMAIL = "desarrollo@localhost"
