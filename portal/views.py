"""Portal del cliente: solo lectura sobre los documentos vigentes de su empresa (CLI-01 a CLI-08).

Toda consulta parte de `visibles_para(request.user)`: ninguna vista recibe la empresa por
parámetro, y lo ajeno o lo que está en la papelera responde 404 igual que lo que no existe
(DOC-06). Ninguna vista admite otro método que GET (CLI-05).
"""

import datetime

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.views import View
from django.views.generic import TemplateView

from core.mixins import ClienteMixin
from core.navegacion import BUSQUEDA_MAXIMO
from core.paginacion import paginar
from documentos import services
from documentos.models import Documento
from empresas.models import Carpeta
from sitio.services import contacto_publico

# Un documento lleva la etiqueta "Nuevo" durante estos días desde que se subió o se reemplazó.
NUEVO_DIAS = 14
RECIENTES = 10

ORDENES = (("fecha", "Más recientes"), ("nombre", "Por nombre"))


def marcar_nuevos(documentos):
    """Devuelve los documentos como lista, cada uno con `nuevo` según la fecha de su archivo."""
    limite = timezone.now() - datetime.timedelta(days=NUEVO_DIAS)
    documentos = list(documentos)
    for documento in documentos:
        documento.nuevo = documento.version_vigente.subido_en > limite
    return documentos


class VistaDelPortal(ClienteMixin, TemplateView):
    http_method_names = ["get"]

    def documentos(self):
        return Documento.objects.visibles_para(self.request.user).con_vigente()

    def carpetas(self):
        return Carpeta.objects.visibles_para(self.request.user).con_resumen()

    def pagina_de(self, documentos):
        pagina = paginar(self.request, documentos)
        pagina.object_list = marcar_nuevos(pagina.object_list)
        return pagina


class Inicio(VistaDelPortal):
    template_name = "portal/inicio.html"
    seccion = "inicio"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        carpetas = list(self.carpetas())
        hay_documentos = any(carpeta.cantidad for carpeta in carpetas)
        contexto.update(
            empresa=self.request.user.empresa,
            carpetas=carpetas,
            hay_documentos=hay_documentos,
            # Solo en el estado vacío: a quién pedirle los documentos (CLI-06).
            contacto=None if hay_documentos else contacto_publico(),
            recientes=(
                marcar_nuevos(self.documentos().recientes()[:RECIENTES]) if hay_documentos else []
            ),
        )
        return contexto


class Carpetas(VistaDelPortal):
    template_name = "portal/carpetas.html"
    seccion = "carpetas"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["carpetas"] = list(self.carpetas())
        return contexto


class CarpetaDetalle(VistaDelPortal):
    """Documentos de una carpeta, por fecha o por nombre (CLI-02)."""

    template_name = "portal/carpeta.html"
    seccion = "carpetas"

    @cached_property
    def carpeta(self):
        return get_object_or_404(
            Carpeta.objects.visibles_para(self.request.user), pk=self.kwargs["carpeta"]
        )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        orden = "nombre" if self.request.GET.get("orden") == "nombre" else "fecha"
        documentos = self.documentos().filter(carpeta=self.carpeta)
        documentos = (
            documentos.order_by("titulo", "pk") if orden == "nombre" else documentos.recientes()
        )
        url = reverse("portal:carpeta", args=[self.carpeta.pk])
        contexto.update(
            carpeta=self.carpeta,
            pagina=self.pagina_de(documentos),
            pestanas=[
                {
                    "texto": texto,
                    "url": url if clave == "fecha" else f"{url}?orden={clave}",
                    "activa": clave == orden,
                }
                for clave, texto in ORDENES
            ],
            migas=[("Carpetas", reverse("portal:carpetas")), (self.carpeta.nombre, "")],
        )
        return contexto


class Buscar(VistaDelPortal):
    """Búsqueda por título entre los documentos de la empresa del cliente (CLI-03)."""

    template_name = "portal/buscar.html"
    seccion = ""

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        busqueda = self.request.GET.get("q", "").strip()[:BUSQUEDA_MAXIMO].strip()
        contexto.update(
            busqueda=busqueda,
            buscador_valor=busqueda,
            pagina=self.pagina_de(self.documentos().buscar(busqueda).order_by("titulo", "pk")),
        )
        return contexto


class DocumentoDetalle(VistaDelPortal):
    """Ficha del documento: datos y botones Descargar y Ver en pantalla (CLI-08)."""

    template_name = "portal/documento.html"
    seccion = "carpetas"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        documento = get_object_or_404(self.documentos(), pk=self.kwargs["documento"])
        (documento,) = marcar_nuevos([documento])
        contexto.update(
            documento=documento,
            migas=[
                ("Carpetas", reverse("portal:carpetas")),
                (documento.carpeta.nombre, reverse("portal:carpeta", args=[documento.carpeta_id])),
                (documento.titulo, ""),
            ],
        )
        return contexto


class _Entrega(ClienteMixin, View):
    """Entrega la versión vigente de un documento de la empresa del cliente (DOC-04).

    El documento se busca solo entre los visibles para el usuario: uno de otra empresa, o
    en la papelera, responde 404 igual que uno que no existe (DOC-06). No hay forma de pedir
    una versión anterior.
    """

    http_method_names = ["get"]
    ver = False

    def get(self, request, documento):
        encontrado = get_object_or_404(
            Documento.objects.visibles_para(request.user).select_related(
                "empresa", "version_vigente"
            ),
            pk=documento,
        )
        try:
            return services.entregar(
                encontrado,
                encontrado.version_vigente,
                ver=self.ver,
                actor=request.user,
                request=request,
            )
        except services.ArchivoNoDisponible:
            raise Http404 from None


class DocumentoVer(_Entrega):
    """Ver en pantalla: en el navegador solo PDF, JPG y PNG; el resto se descarga (DOC-05)."""

    ver = True


class DocumentoDescargar(_Entrega):
    pass
