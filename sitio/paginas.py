"""Estructura común de las páginas públicas: navegación, pie y SEO (PUB-04, PUB-07).

Es al sitio público lo que `core.navegacion` al portal y al panel.
"""

from django.conf import settings
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.text import Truncator

from sitio import imagenes, pendientes, services
from sitio.models import DatosNegocio, Servicio

# Rutas del sitio que no son páginas: no llevan el encabezado `X-Robots-Tag`.
SIN_ENCABEZADO = {"sitio:sitemap", "sitio:robots"}
DESCRIPCION_MAXIMA = 160


def paginas_indexables(datos):
    """Nombres de las páginas que hoy tienen contenido para un buscador. Una página sin su
    contenido (PUB-05) no se indexa ni entra al sitemap."""
    contacto = services.contacto_publico(datos)
    formularios = services.formularios_disponibles(datos)
    paginas = []
    if not pendientes.falta(datos.titular):
        paginas.append("sitio:inicio")
    if Servicio.objects.activos().exists():
        paginas.append("sitio:servicios")
    if formularios or contacto.hay:
        paginas.append("solicitudes:contacto")
    if formularios:
        paginas.append("solicitudes:cotizacion")
    if pendientes.politica_disponible(datos):
        paginas.append("sitio:privacidad")
    return paginas


def url_absoluta(ruta):
    """Con SITIO_URL, nunca con el encabezado Host de la petición."""
    return settings.SITIO_URL.rstrip("/") + ruta


class PaginaPublica:
    """Mixin de las vistas públicas. `nombre_de_pagina` es su título; la descripción sale
    del contenido registrado. Una página sin texto propio usa `descripcion_generica`, que solo
    dice qué página es y de quién: sin nombre comercial no se publica."""

    nombre_de_pagina = ""
    descripcion_generica = ""
    http_method_names = ["get", "head"]

    @cached_property
    def datos(self):
        return DatosNegocio.cargar()

    @cached_property
    def contacto(self):
        return services.contacto_publico(self.datos)

    @cached_property
    def formularios(self):
        return services.formularios_disponibles(self.datos)

    @cached_property
    def imagenes_sitio(self):
        return imagenes.de_la_peticion(self.request)

    @cached_property
    def indexable(self):
        return self.request.resolver_match.view_name in paginas_indexables(self.datos)

    def descripcion(self):
        """Texto de `meta description`. Vacío: la etiqueta no se publica."""
        nombre = self.contacto.nombre
        if self.descripcion_generica and nombre:
            return self.descripcion_generica.format(nombre=nombre)
        return ""

    def render_to_response(self, context, **kwargs):
        respuesta = super().render_to_response(context, **kwargs)
        if not self.indexable:
            respuesta["X-Robots-Tag"] = "noindex"
        return respuesta

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        nombre = self.contacto.nombre
        titulo = " · ".join(parte for parte in (self.nombre_de_pagina, nombre) if parte)
        enlaces = [
            ("Inicio", reverse("sitio:inicio")),
            ("Servicios", reverse("sitio:servicios")),
            ("Contacto", reverse("solicitudes:contacto")),
        ]
        pie = list(enlaces)
        if pendientes.politica_disponible(self.datos):
            pie.append(("Política de privacidad", reverse("sitio:privacidad")))
        contexto.update(
            marca_url=reverse("sitio:inicio"),
            enlaces_publicos=enlaces,
            acceso_texto="Acceso clientes",
            acceso_url=reverse("cuentas:acceso"),
            contacto=self.contacto,
            contacto_lineas=self.contacto.lineas,
            enlaces_pie=pie,
            redes_sociales=services.redes_sociales(self.datos),
            formularios_disponibles=self.formularios,
            seo_titulo=titulo,
            seo_descripcion=Truncator(" ".join(self.descripcion().split())).chars(
                DESCRIPCION_MAXIMA
            ),
            seo_sitio=nombre,
            seo_url=url_absoluta(self.request.path),
            seo_indexable=self.indexable,
            seo_imagen=self.imagenes_sitio.foto(imagenes.Ranura.PORTADA),
            sitio_url=settings.SITIO_URL.rstrip("/"),
        )
        return contexto
