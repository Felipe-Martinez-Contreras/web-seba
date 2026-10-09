"""Configuración común a todos los entornos."""

from pathlib import Path

from django.contrib.messages import constants as message_constants
from django.utils.csp import CSP

from config import env
from core.ip import interpretar_redes

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = env.texto("SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env.lista("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "core",
    "empresas",
    "cuentas",
    "auditoria",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.IpClienteMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {"default": env.base_de_datos("DATABASE_URL")}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Caché en base de datos (sección 5): la tabla se crea con `createcachetable`.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache",
    }
}

AUTH_USER_MODEL = "cuentas.Usuario"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.Argon2PasswordHasher"]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {"user_attributes": ("rut", "nombre", "email")},
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-cl"
LANGUAGES = [("es-cl", "Español (Chile)")]
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True
FORMAT_MODULE_PATH = ["config.formats"]

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
# Carpeta con el CSS que compila Tailwind, fuera del código fuente.
_estaticos_compilados = env.texto("ESTATICOS_COMPILADOS_DIR", "")
if _estaticos_compilados:
    STATICFILES_DIRS.append(Path(_estaticos_compilados))

# Sin correo saliente hasta que se configure un proveedor (Etapa 6): enviar falla de forma
# explícita en lugar de intentar un servidor SMTP inexistente.
MAILERS = {}

# Los niveles de los mensajes de Django usan los nombres de los tipos de alerta.
MESSAGE_TAGS = {
    message_constants.DEBUG: "info",
    message_constants.INFO: "info",
    message_constants.SUCCESS: "exito",
    message_constants.WARNING: "advertencia",
    message_constants.ERROR: "error",
}

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# IP real del cliente (AUT-04). Redes CIDR de los proxies de confianza, separadas por comas.
# Vacío: no se lee ningún encabezado y la IP es la de la conexión.
PROXY_CONFIANZA_REDES = env.lista("PROXY_CONFIANZA_REDES")
PROXY_CONFIANZA_ENCABEZADO = env.texto("PROXY_CONFIANZA_ENCABEZADO", "X-Forwarded-For")
interpretar_redes(PROXY_CONFIANZA_REDES)

# Bloqueo temporal por intentos fallidos de acceso (AUT-04).
ACCESO_INTENTOS_MAXIMOS = env.entero("ACCESO_INTENTOS_MAXIMOS", 5)
ACCESO_INTENTOS_MAXIMOS_IP = env.entero("ACCESO_INTENTOS_MAXIMOS_IP", 30)
ACCESO_VENTANA_MINUTOS = env.entero("ACCESO_VENTANA_MINUTOS", 15)
ACCESO_BLOQUEO_MINUTOS = env.entero("ACCESO_BLOQUEO_MINUTOS", 15)

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# Política estricta: sin scripts ni estilos en línea, y todo desde el propio origen.
SECURE_CSP = {
    "default-src": [CSP.NONE],
    "script-src": [CSP.SELF],
    "style-src": [CSP.SELF],
    "img-src": [CSP.SELF],
    "font-src": [CSP.SELF],
    "connect-src": [CSP.SELF],
    "form-action": [CSP.SELF],
    "base-uri": [CSP.NONE],
    "frame-ancestors": [CSP.NONE],
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "core.logs.FormatoJson"}},
    "handlers": {
        "consola": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "json",
        }
    },
    "root": {"handlers": ["consola"], "level": env.texto("NIVEL_DE_LOG", "INFO")},
    # Sin los manejadores propios de Django: todo sale una sola vez, en JSON, por la raíz.
    "loggers": {
        "django": {"handlers": [], "propagate": True},
        "django.server": {"handlers": [], "propagate": True},
    },
}
