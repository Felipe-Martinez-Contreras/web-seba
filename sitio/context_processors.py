from django.utils.functional import SimpleLazyObject

from sitio import fotos, pendientes
from sitio.models import DatosNegocio


def marca(request):
    """Nombre comercial para la marca de todas las pantallas (DISENO.md, diferencia 10) y
    fotografía de las pantallas de acceso.

    El nombre es perezoso: la consulta solo ocurre si la plantilla lo usa. Sin nombre
    registrado queda vacío y la marca no se muestra.
    """
    return {
        "foto_acceso": fotos.ACCESO,
        "marca_nombre": SimpleLazyObject(
            lambda: pendientes.disponible(DatosNegocio.cargar().nombre_comercial)
        ),
    }
