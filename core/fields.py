from django.db import models

from core import rut
from core.validators import validar_rut


class CampoRut(models.CharField):
    """RUT guardado en forma normalizada (sin puntos ni guion, K mayúscula).

    Normaliza al asignar desde formularios, al guardar y al consultar, de modo que
    `filter(rut="12.345.678-5")` y `filter(rut="123456785")` son equivalentes.
    """

    default_validators = [validar_rut]
    description = "RUT chileno normalizado"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 9)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        value = super().to_python(value)
        return value if value is None else rut.normalizar(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return value if value is None else rut.normalizar(value)

    def pre_save(self, model_instance, add):
        valor = getattr(model_instance, self.attname)
        if valor is not None:
            valor = rut.normalizar(valor)
            setattr(model_instance, self.attname, valor)
        return valor
