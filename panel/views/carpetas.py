"""Carpetas de un cliente: crear, editar, ordenar y eliminar (ADM-07)."""

from django.contrib import messages
from django.shortcuts import redirect
from django.views import View
from django.views.generic import FormView

from empresas import services
from empresas.forms import FormularioCarpeta
from panel.views.base import VistaDeCarpeta, VistaDeCliente


class CarpetaNueva(VistaDeCliente, FormView):
    template_name = "panel/carpeta_formulario.html"
    form_class = FormularioCarpeta
    pestana = "documentos"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "empresa": self.empresa}

    def form_valid(self, form):
        carpeta = services.crear_carpeta(
            self.empresa,
            nombre=form.cleaned_data["nombre"],
            descripcion=form.cleaned_data["descripcion"],
            actor=self.request.user,
            request=self.request,
        )
        messages.success(self.request, f"Se creó la carpeta {carpeta.nombre}.")
        return redirect(self.url_ficha())

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["migas"] = [*contexto["migas"], ("Nueva carpeta", "")]
        return contexto


class CarpetaEditar(VistaDeCarpeta, FormView):
    template_name = "panel/carpeta_formulario.html"
    form_class = FormularioCarpeta

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "empresa": self.empresa, "carpeta": self.carpeta}

    def form_valid(self, form):
        if form.has_changed():
            services.editar_carpeta(
                self.carpeta,
                nombre=form.cleaned_data["nombre"],
                descripcion=form.cleaned_data["descripcion"],
                actor=self.request.user,
                request=self.request,
            )
            messages.success(self.request, "Se guardaron los cambios de la carpeta.")
        return redirect(self.url_ficha())

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["carpeta"] = self.carpeta
        contexto["migas"] = [*contexto["migas"], ("Editar carpeta", "")]
        return contexto


class CarpetaMover(VistaDeCarpeta, View):
    http_method_names = ["post"]

    def post(self, request, **kwargs):
        direccion = request.POST.get("direccion")
        if direccion in (services.SUBIR, services.BAJAR):
            services.mover_carpeta(self.carpeta, direccion)
        return redirect(self.url_ficha())


class CarpetaEliminar(VistaDeCarpeta, View):
    """Solo POST, tras el diálogo de confirmación."""

    http_method_names = ["post"]

    def post(self, request, **kwargs):
        nombre = self.carpeta.nombre
        services.eliminar_carpeta(self.carpeta, actor=request.user, request=request)
        messages.success(request, f"Se eliminó la carpeta {nombre}.")
        return redirect(self.url_ficha())
