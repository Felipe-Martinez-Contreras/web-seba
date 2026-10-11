"""Contenido del sitio: datos del negocio y servicios (ADM-10)."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.views import View
from django.views.generic import FormView, TemplateView

from core.mixins import AdministradorMixin
from sitio import pendientes, services
from sitio.forms import FormularioDatosNegocio, FormularioServicio
from sitio.models import DatosNegocio, Servicio

_GRUPOS = (
    ("Identidad y portada", ("nombre_comercial", "titular", "bajada", "presentacion")),
    ("Contacto", ("telefono", "email_publico", "whatsapp", "ubicacion", "horario")),
    ("Redes sociales", ("instagram", "linkedin", "facebook")),
    ("Política de privacidad", ("politica_privacidad",)),
)
_PESTANAS = (("panel:contenido", "Datos del negocio"), ("panel:servicios", "Servicios"))


class _VistaDeContenido(AdministradorMixin):
    seccion = "contenido"
    ruta = ""

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["pestanas"] = [
            {"texto": texto, "url": reverse(ruta), "activa": ruta == self.ruta}
            for ruta, texto in _PESTANAS
        ]
        return contexto


class Contenido(_VistaDeContenido, FormView):
    """Datos del negocio. Cada dato pendiente lleva el marcador [COMPLETAR] (PUB-06)."""

    template_name = "panel/contenido.html"
    form_class = FormularioDatosNegocio
    ruta = "panel:contenido"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": DatosNegocio.cargar()}

    def form_valid(self, form):
        if form.has_changed():
            services.guardar_datos(form)
            messages.success(self.request, "Se guardaron los datos del negocio.")
        return redirect("panel:contenido")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        formulario = contexto["form"]
        datos = formulario.instance
        faltantes = {
            campo
            for campo in pendientes.CAMPOS_REQUERIDOS
            if pendientes.falta(getattr(datos, campo))
        }
        if not pendientes.politica_disponible(datos):
            faltantes.add("politica_privacidad")
        contexto.update(
            grupos=[
                (titulo, [(formulario[campo], campo in faltantes) for campo in campos])
                for titulo, campos in _GRUPOS
            ],
            marcador=pendientes.MARCADOR,
            politica_de_prueba=pendientes.de_prueba(datos.politica_privacidad),
        )
        return contexto


class Servicios(_VistaDeContenido, TemplateView):
    template_name = "panel/servicios.html"
    ruta = "panel:servicios"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["servicios"] = list(Servicio.objects.all())
        return contexto


class _VistaDeServicio(_VistaDeContenido):
    ruta = "panel:servicios"

    @cached_property
    def servicio(self):
        return get_object_or_404(Servicio, pk=self.kwargs["servicio"])


def _migas(titulo):
    return [("Servicios", reverse("panel:servicios")), (titulo, "")]


class ServicioNuevo(_VistaDeContenido, FormView):
    template_name = "panel/servicio_formulario.html"
    form_class = FormularioServicio
    ruta = "panel:servicios"

    def form_valid(self, form):
        servicio = services.crear_servicio(form)
        messages.success(self.request, f"Se creó el servicio {servicio.nombre}.")
        return redirect("panel:servicios")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["migas"] = _migas("Nuevo servicio")
        return contexto


class ServicioEditar(_VistaDeServicio, FormView):
    template_name = "panel/servicio_formulario.html"
    form_class = FormularioServicio

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": self.servicio}

    def form_valid(self, form):
        if form.has_changed():
            services.editar_servicio(form)
            messages.success(self.request, "Se guardaron los cambios del servicio.")
        return redirect("panel:servicios")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["edicion"] = True
        contexto["migas"] = _migas("Editar servicio")
        return contexto


class ServicioMover(_VistaDeServicio, View):
    http_method_names = ["post"]

    def post(self, request, **kwargs):
        direccion = request.POST.get("direccion")
        if direccion in (services.SUBIR, services.BAJAR):
            services.mover_servicio(self.servicio, direccion)
        return redirect("panel:servicios")


class ServicioEstado(_VistaDeServicio, View):
    """Activa o desactiva el servicio. No hay borrado: las solicitudes lo siguen nombrando."""

    http_method_names = ["post"]

    def post(self, request, **kwargs):
        activo = request.POST.get("activo") == "si"
        if services.cambiar_estado_servicio(self.servicio, activo):
            if activo:
                messages.success(request, f"{self.servicio.nombre} volvió a mostrarse en el sitio.")
            else:
                messages.success(request, f"{self.servicio.nombre} dejó de mostrarse en el sitio.")
        return redirect("panel:servicios")
