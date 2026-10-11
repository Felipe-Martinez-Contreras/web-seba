"""Solicitudes del sitio público: bandeja, detalle, estado, notas y reintento (SOL-09, SOL-10).

Las respuestas al visitante se envían por correo, fuera de la plataforma: aquí no hay
mensajería.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.views import View
from django.views.generic import TemplateView

from core import correo
from core.mixins import AdministradorMixin
from core.paginacion import paginar
from solicitudes import services
from solicitudes.forms import FormularioEstado, FormularioFiltros, FormularioNotas
from solicitudes.models import Solicitud

_RUTA_DE = {
    Solicitud.Tipo.CONSULTA: "panel:solicitudes_consultas",
    Solicitud.Tipo.COTIZACION: "panel:solicitudes_cotizaciones",
}
_PESTANAS = ((Solicitud.Tipo.CONSULTA, "Consultas"), (Solicitud.Tipo.COTIZACION, "Cotizaciones"))
ANTIGUAS = "antiguas"


def pestanas(tipo_activo):
    return [
        {"texto": texto, "url": reverse(_RUTA_DE[tipo]), "activa": tipo == tipo_activo}
        for tipo, texto in _PESTANAS
    ]


class Solicitudes(AdministradorMixin, TemplateView):
    """Bandeja de un tipo de solicitud, con filtros, búsqueda, orden por fecha y páginas."""

    template_name = "panel/solicitudes.html"
    seccion = "solicitudes"
    tipo = Solicitud.Tipo.CONSULTA

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        filtros = {
            campo: self.request.GET.get(campo, "") for campo in ("q", "estado", "desde", "hasta")
        }
        formulario = FormularioFiltros(filtros if any(filtros.values()) else None)
        solicitudes = Solicitud.objects.filter(tipo=self.tipo).select_related("servicio")
        if formulario.is_bound:
            # Con un filtro inválido no se muestra nada: mostrar todo sugeriría que se aplicó.
            if formulario.is_valid():
                datos = formulario.cleaned_data
                solicitudes = solicitudes.buscar(datos["q"]).filtrar(
                    estado=datos["estado"], desde=datos["desde"], hasta=datos["hasta"]
                )
            else:
                solicitudes = solicitudes.none()
        antiguas_primero = self.request.GET.get("orden") == ANTIGUAS
        contexto.update(
            tipo=self.tipo,
            es_cotizacion=self.tipo == Solicitud.Tipo.COTIZACION,
            form=formulario,
            con_filtros=formulario.is_bound,
            pagina=paginar(
                self.request,
                solicitudes.order_by("creado_en" if antiguas_primero else "-creado_en"),
            ),
            pestanas=pestanas(self.tipo),
            antiguas_primero=antiguas_primero,
            url_sin_filtros=reverse(_RUTA_DE[self.tipo]),
            orden_siguiente=None if antiguas_primero else ANTIGUAS,
        )
        return contexto


class _VistaDeSolicitud(AdministradorMixin):
    seccion = "solicitudes"

    @cached_property
    def solicitud(self):
        return get_object_or_404(
            Solicitud.objects.select_related("servicio"), pk=self.kwargs["solicitud"]
        )

    def url_detalle(self):
        return reverse("panel:solicitud", args=[self.solicitud.pk])


class SolicitudDetalle(_VistaDeSolicitud, TemplateView):
    template_name = "panel/solicitud.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        solicitud = self.solicitud
        contexto.update(
            solicitud=solicitud,
            form_estado=FormularioEstado(initial={"estado": solicitud.estado}),
            form_notas=FormularioNotas(initial={"notas_internas": solicitud.notas_internas}),
            puede_reintentar=solicitud.notificacion != Solicitud.Notificacion.ENVIADA,
            migas=[
                (
                    "Cotizaciones" if solicitud.tipo == Solicitud.Tipo.COTIZACION else "Consultas",
                    reverse(_RUTA_DE[solicitud.tipo]),
                ),
                (solicitud.nombre, ""),
            ],
        )
        return contexto


class SolicitudEstado(_VistaDeSolicitud, View):
    http_method_names = ["post"]

    def post(self, request, **kwargs):
        formulario = FormularioEstado(request.POST)
        if formulario.is_valid() and services.cambiar_estado(
            self.solicitud, formulario.cleaned_data["estado"], actor=request.user, request=request
        ):
            messages.success(
                request, f"La solicitud quedó como {self.solicitud.get_estado_display()}."
            )
        return redirect(self.url_detalle())


class SolicitudNotas(_VistaDeSolicitud, View):
    http_method_names = ["post"]

    def post(self, request, **kwargs):
        formulario = FormularioNotas(request.POST)
        if formulario.is_valid():
            services.guardar_notas(self.solicitud, formulario.cleaned_data["notas_internas"])
            messages.success(request, "Se guardaron las notas internas.")
        else:
            messages.error(request, "Las notas no se guardaron: superan el largo permitido.")
        return redirect(self.url_detalle())


class SolicitudReintentar(_VistaDeSolicitud, View):
    """Vuelve a intentar la notificación y dice qué pasó, sin afirmar lo que no ocurrió (R4)."""

    http_method_names = ["post"]

    def post(self, request, **kwargs):
        resultado = services.reintentar(self.solicitud, actor=request.user, request=request)
        if resultado == correo.Resultado.ENVIADA:
            messages.success(request, "La notificación se envió.")
        elif resultado == correo.Resultado.FALLIDA:
            messages.error(request, "La notificación volvió a fallar. La solicitud sigue guardada.")
        elif resultado == correo.Resultado.NO_CONFIGURADA:
            messages.warning(
                request,
                "No se envió: falta configurar el correo saliente o los destinatarios de "
                "las notificaciones.",
            )
        else:
            messages.info(request, "Esta solicitud ya había sido notificada.")
        return redirect(self.url_detalle())
