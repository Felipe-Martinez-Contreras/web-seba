from django.utils.functional import SimpleLazyObject

from sitio import imagenes, pendientes
from sitio.models import DatosNegocio


def marca(request):
    """Nombre comercial para la marca de todas las pantallas (DISENO.md, diferencia 10) e
    imágenes del sitio: símbolo, íconos y fotografía de las pantallas de acceso (DEC-205).

    Todo es perezoso: la consulta solo ocurre si la plantilla lo usa. Sin nombre registrado
    queda vacío y la marca no se muestra.
    """
    return {
        "imagenes_sitio": SimpleLazyObject(lambda: imagenes.de_la_peticion(request)),
        "marca_nombre": SimpleLazyObject(
            lambda: pendientes.disponible(DatosNegocio.cargar().nombre_comercial)
        ),
    }
