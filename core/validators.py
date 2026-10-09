from django.core.exceptions import ValidationError

from core import rut


def validar_rut(valor):
    if not rut.es_valido(valor):
        raise ValidationError(
            "Ingrese un RUT válido, por ejemplo 12.345.678-5.", code="rut_invalido"
        )
