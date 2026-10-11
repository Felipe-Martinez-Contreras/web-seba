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
    "config.apps.AdminTecnicoConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # Solo por la búsqueda sin tildes (`unaccent`) del portal.
    "django.contrib.postgres",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "core",
    "empresas",
    "cuentas",
    "auditoria",
    "documentos",
    "portal",
    "panel",
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
    "cuentas.middleware.CorteDeSesionMiddleware",
    "django_otp.middleware.OTPMiddleware",
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
AUTHENTICATION_BACKENDS = ["cuentas.backends.BackendRut"]
LOGIN_URL = "cuentas:acceso"

# URL pública del sitio, sin barra final. Con ella se arman los enlaces de activación y de
# recuperación: nunca con el encabezado Host de la petición.
SITIO_URL = env.texto("SITIO_URL", "http://localhost:8000")

# Ruta del admin de Django (ADM-12), sin barras. Vacía: no se publica.
DJANGO_ADMIN_RUTA = env.texto("DJANGO_ADMIN_RUTA", "").strip("/")

# Enlaces de un solo uso (AUT-06, AUT-07).
ENLACE_ACTIVACION_HORAS = env.entero("ENLACE_ACTIVACION_HORAS", 72)
ENLACE_RESTABLECIMIENTO_MINUTOS = env.entero("ENLACE_RESTABLECIMIENTO_MINUTOS", 60)
RECUPERACION_MAXIMO_POR_RUT = env.entero("RECUPERACION_MAXIMO_POR_RUT", 3)
RECUPERACION_MAXIMO_POR_IP = env.entero("RECUPERACION_MAXIMO_POR_IP", 10)

# 2FA de administradores (AUT-10). Tras usar un enlace, la sesión tiene este plazo para enrolar.
ENROLAMIENTO_2FA_MINUTOS = env.entero("ENROLAMIENTO_2FA_MINUTOS", 30)
OTP_ADMIN_HIDE_SENSITIVE_DATA = True

# Carpetas que se crean con cada empresa nueva, si el administrador no desmarca la opción
# (ADM-04). Cambiar la lista no altera las empresas que ya existen.
CARPETAS_BASE = [
    "Matrices de riesgos",
    "Protocolos MINSAL",
    "Reglamento interno",
    "Formatos de inspección",
    "Documentos preventivos",
]

# Documentos (DOC-01 a DOC-04). "local" guarda en DOCUMENTOS_DIR, fuera de toda ruta pública;
# "s3", en un bucket privado compatible con S3. El código de subida y de descarga es el mismo.
DOCUMENTOS_ALMACENAMIENTO = env.texto("DOCUMENTOS_ALMACENAMIENTO", "local")
DOCUMENTOS_DIR = env.texto("DOCUMENTOS_DIR", "/var/app/media")
S3_BUCKET = env.texto("S3_BUCKET", "")
S3_ENDPOINT_URL = env.texto("S3_ENDPOINT_URL", "")
S3_REGION = env.texto("S3_REGION", "")
S3_ACCESS_KEY_ID = env.texto("S3_ACCESS_KEY_ID", "")
S3_SECRET_ACCESS_KEY = env.texto("S3_SECRET_ACCESS_KEY", "")
# Lista blanca de extensiones (DOC-01). Solo admite las que la validación sabe comprobar.
DOCUMENTOS_FORMATOS = env.lista(
    "DOCUMENTOS_FORMATOS", ["pdf", "docx", "xlsx", "pptx", "jpg", "jpeg", "png"]
)
DOCUMENTOS_TAMANO_MAXIMO_MB = env.entero("DOCUMENTOS_TAMANO_MAXIMO_MB", 25)
# Vigencia de la URL firmada de descarga. Nunca supera los 120 segundos (DOC-04).
DESCARGA_URL_SEGUNDOS = env.entero("DESCARGA_URL_SEGUNDOS", 120)
# Días que un documento eliminado se puede restaurar antes de `purgar_papelera` (ADM-09).
PAPELERA_DIAS = env.entero("PAPELERA_DIAS", 30)
# Archivos por petición en la subida sin JavaScript; con JavaScript va uno por petición.
DATA_UPLOAD_MAX_NUMBER_FILES = 20
# El primero corta, antes de leer el cuerpo, una petición más grande que el tope de subida.
# Los otros dos son los de Django: lo que pasa de 2,5 MB va a un archivo temporal en disco.
FILE_UPLOAD_HANDLERS = [
    "documentos.subida.LimiteDePeticion",
    "django.core.files.uploadhandler.MemoryFileUploadHandler",
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
]

# Retención de la auditoría (AUD-03): el comando `depurar_auditoria` borra lo anterior.
AUDITORIA_RETENCION_MESES = env.entero("AUDITORIA_RETENCION_MESES", 24)

# El envío de correo sale de la petición (core.tareas) y parte tras esta espera, más una
# parte al azar de hasta el mismo valor. En las pruebas es inmediato.
TAREAS_SINCRONAS = False
TAREAS_ESPERA_SEGUNDOS = 2

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

# Correo saliente por SMTP. Sin CORREO_HOST no hay ningún mailer: el envío se informa como
# "no configurado" en lugar de intentar un servidor inexistente (R4).
MAILERS = {}
_correo_host = env.texto("CORREO_HOST", "")
if _correo_host:
    MAILERS["default"] = {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "OPTIONS": {
            "host": _correo_host,
            "port": env.entero("CORREO_PUERTO", 587),
            "username": env.texto("CORREO_USUARIO", ""),
            "password": env.texto("CORREO_CLAVE", ""),
            "use_tls": env.booleano("CORREO_TLS", True),
            "timeout": 10,
        },
    }
DEFAULT_FROM_EMAIL = env.texto("CORREO_REMITENTE", "")

# Los niveles de los mensajes de Django usan los nombres de los tipos de alerta.
MESSAGE_TAGS = {
    message_constants.DEBUG: "info",
    message_constants.INFO: "info",
    message_constants.SUCCESS: "exito",
    message_constants.WARNING: "advertencia",
    message_constants.ERROR: "error",
}

# Sesiones (AUT-09): vencen tras un tiempo sin uso y no sobreviven al cierre del navegador.
SESSION_COOKIE_AGE = env.entero("SESION_MINUTOS_INACTIVIDAD", 60) * 60
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_FAILURE_VIEW = "core.views.csrf_fallido"
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
