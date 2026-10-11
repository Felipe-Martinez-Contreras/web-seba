"""Páginas públicas (PUB-01 a PUB-05, PUB-07). Todo el contenido sale de la base de datos:
lo que no está registrado no se muestra."""

from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView

from sitio import fotos, pendientes
from sitio.models import DatosNegocio, Servicio
from sitio.paginas import PaginaPublica, paginas_indexables, url_absoluta
from solicitudes import antispam
from solicitudes.forms import FormularioCotizacion


class Inicio(PaginaPublica, TemplateView):
    """Inicio según la pantalla 1 del mockup: portada, servicios, contacto y pie (PUB-02)."""

    template_name = "sitio/inicio.html"

    def descripcion(self):
        return pendientes.disponible(self.datos.bajada)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(
            titular=pendientes.disponible(self.datos.titular),
            bajada=pendientes.disponible(self.datos.bajada),
            servicios=list(Servicio.objects.activos()),
            foto_portada=fotos.PORTADA,
            foto_contacto=fotos.CONTACTO,
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


@require_GET
def sitemap(request):
    """Solo las páginas públicas con contenido. Nunca portal, panel, acceso ni admin."""
    urls = [url_absoluta(reverse(nombre)) for nombre in paginas_indexables(DatosNegocio.cargar())]
    return render(request, "sitio/sitemap.xml", {"urls": urls}, content_type="application/xml")


@require_GET
def robots(request):
    """No enumera rutas privadas (SEG-13): esas llevan `noindex`, que un buscador solo puede
    leer si no se le prohíbe la página."""
    return render(
        request,
        "sitio/robots.txt",
        {"sitemap": url_absoluta(reverse("sitio:sitemap"))},
        content_type="text/plain; charset=utf-8",
    )
