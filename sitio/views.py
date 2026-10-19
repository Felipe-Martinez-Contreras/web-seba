"""Páginas públicas (PUB-01 a PUB-05, PUB-07). Todo el contenido sale de la base de datos:
lo que no está registrado no se muestra."""

import re

from django.http import Http404, HttpResponse, HttpResponseNotModified
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_safe
from django.views.generic import TemplateView

from sitio import imagenes, pendientes, rubros
from sitio.models import DatosNegocio, Servicio, VarianteImagen
from sitio.paginas import PaginaPublica, paginas_indexables, url_absoluta
from solicitudes import antispam
from solicitudes.forms import FormularioCotizacion


class Inicio(PaginaPublica, TemplateView):
    """Inicio según la pantalla 1 del mockup: portada, servicios, rubros, contacto y pie
    (PUB-02, PUB-09)."""

    template_name = "sitio/inicio.html"

    def descripcion(self):
        return pendientes.disponible(self.datos.bajada)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        titular = pendientes.disponible(self.datos.titular)
        servicios = list(Servicio.objects.activos())
        rubros_publicados = rubros.publicados()
        contexto.update(
            titular=titular,
            bajada=pendientes.disponible(self.datos.bajada),
            servicios=servicios,
            rubros=rubros_publicados,
            foto_portada=self.imagenes_sitio.foto(imagenes.Ranura.PORTADA),
            foto_contacto=self.imagenes_sitio.foto(imagenes.Ranura.CONTACTO),
            # Sin nada que mostrar, la página quedaba en blanco entre el encabezado y el pie
            # y parecía un error: se muestra un estado neutro, sin datos del negocio.
            en_preparacion=not (
                titular or servicios or rubros_publicados or self.formularios or self.contacto.hay
            ),
        )
        if self.formularios:
            contexto.update(
                formulario=FormularioCotizacion(),
                marca=antispam.nueva_marca(),
                url_formulario=reverse("solicitudes:cotizacion"),
            )
        return contexto


class Servicios(PaginaPublica, TemplateView):
    """Servicios activos, en su orden, cada uno con su botón de cotización (PUB-03)."""

    template_name = "sitio/servicios.html"
    nombre_de_pagina = "Servicios"

    def descripcion(self):
        return pendientes.disponible(self.datos.presentacion)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(
            presentacion=pendientes.disponible(self.datos.presentacion),
            servicios=list(Servicio.objects.activos()),
            url_cotizacion=reverse("solicitudes:cotizacion"),
        )
        return contexto


class Privacidad(PaginaPublica, TemplateView):
    """Política de privacidad, con el texto que entrega el responsable (SEG-12)."""

    template_name = "sitio/privacidad.html"
    nombre_de_pagina = "Política de privacidad"
    descripcion_generica = "Política de privacidad de {nombre}."

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        if pendientes.politica_disponible(self.datos):
            contexto["politica"] = self.datos.politica_privacidad
        return contexto


@require_safe
def sitemap(request):
    """Solo las páginas públicas con contenido. Nunca portal, panel, acceso ni admin."""
    urls = [url_absoluta(reverse(nombre)) for nombre in paginas_indexables(DatosNegocio.cargar())]
    return render(request, "sitio/sitemap.xml", {"urls": urls}, content_type="application/xml")


@require_safe
def robots(request):
    """No enumera rutas privadas (SEG-13): esas llevan `noindex`, que un buscador solo puede
    leer si no se le prohíbe la página."""
    return render(
        request,
        "sitio/robots.txt",
        {"sitemap": url_absoluta(reverse("sitio:sitemap"))},
        content_type="text/plain; charset=utf-8",
    )


_NOMBRE_IMAGEN = re.compile(r"([0-9a-f]{64})\.(webp|png|ico)")
_UN_ANO = 365 * 24 * 3600


@require_safe
def imagen(request, nombre):
    """Una imagen subida desde el panel, ya re-codificada (DEC-205). La URL lleva el SHA-256
    del contenido: no cambia nunca, así que se guarda en caché por un año, en el navegador y
    en Cloudflare, y una imagen nueva tiene otra URL."""
    coincidencia = _NOMBRE_IMAGEN.fullmatch(nombre)
    if not coincidencia:
        raise Http404
    sha256, extension = coincidencia.groups()
    variante = VarianteImagen.objects.filter(sha256=sha256).only("tipo_mime").first()
    if variante is None or imagenes.EXTENSIONES[variante.tipo_mime] != extension:
        raise Http404
    etiqueta = f'"{sha256}"'
    if etiqueta in request.headers.get("If-None-Match", ""):
        respuesta = HttpResponseNotModified()
    else:
        contenido = VarianteImagen.objects.values_list("contenido", flat=True).get(pk=variante.pk)
        respuesta = HttpResponse(bytes(contenido), content_type=variante.tipo_mime)
    respuesta["ETag"] = etiqueta
    respuesta["Cache-Control"] = f"public, max-age={_UN_ANO}, immutable"
    respuesta["X-Content-Type-Options"] = "nosniff"
    respuesta["Content-Security-Policy"] = "sandbox"
    return respuesta
