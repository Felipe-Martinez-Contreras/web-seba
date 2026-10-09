"""Desarrollo local."""

from .base import *  # noqa: F403
from .base import env

DEBUG = True
ALLOWED_HOSTS = env.lista("ALLOWED_HOSTS", ["localhost", "127.0.0.1"])

# Los correos se imprimen en la consola del contenedor.
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}
