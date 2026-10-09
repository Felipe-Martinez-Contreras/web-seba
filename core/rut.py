"""Utilidades de RUT chileno: normalización, dígito verificador y formato."""

import re

# Forma normalizada: cuerpo de 1 a 8 dígitos y dígito verificador, sin puntos ni guion.
PATRON_NORMALIZADO = r"^[1-9][0-9]{0,7}[0-9K]$"
_NORMALIZADO = re.compile(PATRON_NORMALIZADO)
_SEPARADORES = re.compile(r"[.\-\s]")


def normalizar(valor):
    """Quita puntos, guion, espacios y ceros iniciales, y pasa la K a mayúscula.

    No valida: `normalizar("abc")` devuelve "ABC". Use `es_valido` para validar.
    """
    return _SEPARADORES.sub("", str(valor or "")).upper().lstrip("0")


def digito_verificador(cuerpo):
    """Calcula el dígito verificador (módulo 11) del cuerpo numérico de un RUT."""
    suma = 0
    factor = 2
    for digito in reversed(str(cuerpo)):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - suma % 11
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


def es_valido(valor):
    """Indica si el valor, con o sin puntos y guion, es un RUT con dígito verificador correcto."""
    rut = normalizar(valor)
    if not _NORMALIZADO.match(rut):
        return False
    return digito_verificador(rut[:-1]) == rut[-1]


def formatear(valor):
    """Devuelve el RUT como 12.345.678-5. Si no tiene forma de RUT, lo devuelve sin cambios."""
    rut = normalizar(valor)
    if not _NORMALIZADO.match(rut):
        return str(valor or "")
    cuerpo = f"{int(rut[:-1]):,}".replace(",", ".")
    return f"{cuerpo}-{rut[-1]}"
