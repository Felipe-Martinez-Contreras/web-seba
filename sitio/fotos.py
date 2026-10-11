"""Fotografías del sitio (PUB-08). Origen, autor y licencia de cada una: docs/FOTOS.md.

Son archivos estáticos propios. Para reemplazar una foto basta cambiar sus dos archivos
(1.920 y 960 px de ancho) y, si la escena cambia, su texto alternativo aquí.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Foto:
    archivo: str
    archivo_movil: str
    ancho: int
    alto: int
    # Describe la escena, sin atribuirla al negocio: ninguna foto de banco muestra al
    # profesional, a sus clientes ni sus obras.
    alt: str


PORTADA = Foto(
    "img/portada.webp",
    "img/portada-960.webp",
    1920,
    1351,
    "Obra en construcción al atardecer, con una grúa torre y edificios al fondo.",
)
CONTACTO = Foto(
    "img/contacto.webp",
    "img/contacto-960.webp",
    1920,
    1280,
    "Casco de seguridad blanco colgado de un gancho en una planta industrial.",
)
ACCESO = Foto(
    "img/acceso.webp",
    "img/acceso-960.webp",
    1920,
    650,
    "Casco de seguridad amarillo sobre un fondo oscuro.",
)
