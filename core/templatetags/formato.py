from django import template

from core import rut as utilidades_rut

register = template.Library()


@register.filter
def rut(valor):
    """Muestra un RUT como 12.345.678-5."""
    return utilidades_rut.formatear(valor)
