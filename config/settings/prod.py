"""Producción. Se niega a arrancar si la configuración mínima falta o es insegura."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import ALLOWED_HOSTS, BASE_DIR, SECRET_KEY, env

DEBUG = False

# SECRET_KEY y DATABASE_URL ya son obligatorias en base.py.
if SECRET_KEY == env.CLAVE_DE_EJEMPLO:
    raise ImproperlyConfigured(
        "SECRET_KEY tiene el valor de ejemplo de .env.example. Genere una clave propia."
    )
if len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("SECRET_KEY debe tener al menos 50 caracteres.")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Falta la variable de entorno ALLOWED_HOSTS.")
if "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS no admite el comodín '*'.")

CSRF_TRUSTED_ORIGINS = env.lista("CSRF_TRUSTED_ORIGINS")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# HSTS parte bajo y se sube al confirmar que todo funciona con HTTPS (SEG-01).
SECURE_HSTS_SECONDS = env.entero("SECURE_HSTS_SECONDS", 3600)

# Solo producción recolecta los estáticos; en desarrollo se sirven desde su origen.
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
