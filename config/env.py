"""Lectura de variables de entorno para la configuración."""

import os
from urllib.parse import unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured

# Valor de SECRET_KEY publicado en .env.example. Sirve solo para desarrollo:
# la configuración de producción se niega a arrancar con él.
CLAVE_DE_EJEMPLO = "clave-de-ejemplo-solo-para-desarrollo-local-no-usar-en-produccion"

_VERDADEROS = {"1", "true", "si", "sí", "yes", "on"}
_FALSOS = {"0", "false", "no", "off", ""}
_SIN_DEFECTO = object()


def texto(nombre, defecto=_SIN_DEFECTO):
    """Devuelve la variable; si falta o está vacía, el valor por defecto o un error."""
    valor = os.environ.get(nombre, "").strip()
    if valor:
        return valor
    if defecto is _SIN_DEFECTO:
        raise ImproperlyConfigured(f"Falta la variable de entorno {nombre}.")
    return defecto


def booleano(nombre, defecto=False):
    valor = os.environ.get(nombre)
    if valor is None:
        return defecto
    valor = valor.strip().lower()
    if valor in _VERDADEROS:
        return True
    if valor in _FALSOS:
        return False
    raise ImproperlyConfigured(f"La variable de entorno {nombre} debe ser verdadero o falso.")


def entero(nombre, defecto):
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        return defecto
    try:
        return int(valor)
    except ValueError:
        raise ImproperlyConfigured(
            f"La variable de entorno {nombre} debe ser un número entero."
        ) from None


def lista(nombre, defecto=()):
    """Lista separada por comas, sin elementos vacíos."""
    valor = os.environ.get(nombre, "")
    elementos = [elemento.strip() for elemento in valor.split(",") if elemento.strip()]
    return elementos or list(defecto)


def base_de_datos(nombre="DATABASE_URL"):
    """Convierte una URL postgres://usuario:clave@host:puerto/base en la entrada de DATABASES."""
    url = urlsplit(texto(nombre))
    base = url.path.lstrip("/")
    if url.scheme not in {"postgres", "postgresql"} or not url.hostname or not base:
        # El mensaje no incluye la URL: contiene la contraseña.
        raise ImproperlyConfigured(
            f"La variable de entorno {nombre} debe tener la forma "
            "postgres://usuario:clave@host:puerto/base."
        )
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(base),
        "USER": unquote(url.username or ""),
        "PASSWORD": unquote(url.password or ""),
        "HOST": url.hostname,
        "PORT": str(url.port or ""),
    }
