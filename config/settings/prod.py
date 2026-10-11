"""Producción. Se niega a arrancar si la configuración mínima falta o es insegura."""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import ALLOWED_HOSTS, BASE_DIR, PROXY_CONFIANZA_REDES, SECRET_KEY, SITIO_URL, env

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

# Debe declararse siempre, aunque sea vacía: detrás de un proxy, sin ella todos los
# clientes compartirían la IP del proxy y el bloqueo por IP los afectaría a todos.
if "PROXY_CONFIANZA_REDES" not in os.environ:
    raise ImproperlyConfigured(
        "Falta la variable de entorno PROXY_CONFIANZA_REDES. Indique las redes del proxy "
        "o déjela vacía si la aplicación recibe las conexiones directamente."
    )

# Los enlaces de activación y recuperación se arman con esta URL.
if "SITIO_URL" not in os.environ or not SITIO_URL.startswith("https://"):
    raise ImproperlyConfigured("Falta la variable de entorno SITIO_URL o no empieza con https://.")

# El almacenamiento de documentos se declara siempre: no se cae al disco local por omisión.
if "DOCUMENTOS_ALMACENAMIENTO" not in os.environ:
    raise ImproperlyConfigured(
        "Falta la variable de entorno DOCUMENTOS_ALMACENAMIENTO (local o s3)."
    )

# HTTPS detrás de un proxy que termina TLS (SEG-01): sin este encabezado Django cree que
# toda petición llegó por HTTP y la redirección a HTTPS no termina nunca. Va de la mano con
# PROXY_CONFIANZA_REDES: con proxy es obligatorio y sin proxy no se admite, porque Django lo
# acepta de cualquier conexión.
_encabezado_https = env.texto("PROXY_HTTPS_ENCABEZADO", "")
if PROXY_CONFIANZA_REDES and not _encabezado_https:
    raise ImproperlyConfigured(
        "Falta la variable de entorno PROXY_HTTPS_ENCABEZADO: el encabezado con que el proxy "
        "indica que la petición llegó por HTTPS (por ejemplo, X-Forwarded-Proto)."
    )
if _encabezado_https and not PROXY_CONFIANZA_REDES:
    raise ImproperlyConfigured(
        "PROXY_HTTPS_ENCABEZADO solo se admite con PROXY_CONFIANZA_REDES: sin un proxy de "
        "confianza, cualquier cliente podría enviar ese encabezado."
    )
if _encabezado_https:
    SECURE_PROXY_SSL_HEADER = ("HTTP_" + _encabezado_https.upper().replace("-", "_"), "https")

# Explícitos (SEG-01): por omisión, solo la URL del sitio.
CSRF_TRUSTED_ORIGINS = env.lista("CSRF_TRUSTED_ORIGINS") or [SITIO_URL]

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# HSTS parte bajo y se sube al confirmar que todo funciona con HTTPS (SEG-01). Extenderlo a
# los subdominios y pedir la precarga en los navegadores son difíciles de revertir: se
# activan por variable, cuando el dominio y sus subdominios ya sirven solo HTTPS.
SECURE_HSTS_SECONDS = env.entero("SECURE_HSTS_SECONDS", 3600)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.booleano("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = env.booleano("SECURE_HSTS_PRELOAD", False)

# Solo producción recolecta los estáticos; en desarrollo se sirven desde su origen.
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
