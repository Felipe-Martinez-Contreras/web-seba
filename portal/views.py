from django.views.generic import TemplateView

from core.mixins import ClienteMixin


class Inicio(ClienteMixin, TemplateView):
    """Inicio del portal. Carpetas, buscador y documentos llegan en las etapas 4 y 5."""

    template_name = "portal/inicio.html"
    seccion = "inicio"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["empresa"] = self.request.user.empresa
        return contexto
