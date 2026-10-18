"""Fotografías del sitio (PUB-08). Origen, autor y licencia de cada una: docs/FOTOS.md.

Las de aquí son las originales, archivos estáticos del repositorio. El administrador puede
reemplazarlas desde el panel (DEC-205, `sitio/imagenes.py`); sin una imagen subida, o si
no se puede leer, el sitio usa estas.
"""

from dataclasses import dataclass, replace

from django.templatetags.static import static


@dataclass(frozen=True)
class Foto:
    archivo: str
    archivo_movil: str
    ancho: int
    alto: int
    # Describe la escena, sin atribuirla al negocio: ninguna foto de banco muestra al
    # profesional, a sus clientes ni sus obras.
    alt: str
    # URL de la versión subida desde el panel. Vacías: los archivos estáticos de arriba.
    url: str = ""
    url_movil: str = ""

    @property
    def src(self):
        return self.url or static(self.archivo)

    @property
    def src_movil(self):
        return self.url_movil or static(self.archivo_movil)

    def subida(self, *, url, url_movil, ancho, alto, alt):
        return replace(self, url=url, url_movil=url_movil, ancho=ancho, alto=alto, alt=alt)


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
