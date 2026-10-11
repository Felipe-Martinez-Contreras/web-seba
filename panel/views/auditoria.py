"""Listado de auditoría: solo lectura (ADM-11)."""

from django.views.generic import TemplateView

from auditoria.forms import FormularioFiltros
from auditoria.models import EventoAuditoria
from core.mixins import AdministradorMixin
from panel.views.base import paginar


class Auditoria(AdministradorMixin, TemplateView):
    template_name = "panel/auditoria.html"
    seccion = "auditoria"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        formulario = FormularioFiltros(self.request.GET or None)
        eventos = EventoAuditoria.objects.select_related("actor", "empresa")
        if formulario.is_bound:
            # Con un filtro inválido no se muestra nada: mostrar todo sugeriría que se aplicó.
            eventos = (
                eventos.filtrar(**formulario.cleaned_data)
                if formulario.is_valid()
                else eventos.none()
            )
        contexto.update(
            form=formulario,
            pagina=paginar(self.request, eventos),
            con_filtros=formulario.is_bound and formulario.has_changed(),
        )
        return contexto
