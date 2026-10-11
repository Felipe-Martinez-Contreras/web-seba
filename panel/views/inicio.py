from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from core.mixins import AdministradorMixin
from cuentas import services
from cuentas.models import Usuario


class Inicio(AdministradorMixin, TemplateView):
    """Inicio del panel. Indicadores, clientes y solicitudes llegan en las etapas 3 y 6."""

    template_name = "panel/inicio.html"
    seccion = "inicio"


class DesbloquearUsuario(AdministradorMixin, View):
    """Desbloqueo manual de un usuario (AUT-04). El usuario se identifica por su UUID."""

    http_method_names = ["post"]

    def post(self, request, uuid):
        usuario = get_object_or_404(Usuario.objects.select_related("empresa"), uuid=uuid)
        services.desbloquear(usuario, actor=request.user, request=request)
        messages.success(request, f"Se desbloqueó el acceso de {usuario.nombre}.")
        return redirect("panel:inicio")
