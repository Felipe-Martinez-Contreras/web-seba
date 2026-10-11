from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import TemplateView

from core.mixins import ClienteMixin
from documentos import services
from documentos.models import Documento


class Inicio(ClienteMixin, TemplateView):
    """Inicio del portal. Carpetas, buscador y documentos llegan en la Etapa 5."""

    template_name = "portal/inicio.html"
    seccion = "inicio"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["empresa"] = self.request.user.empresa
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
