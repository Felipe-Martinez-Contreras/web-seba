"""Usuarios de un cliente: alta, edición, estado, enlaces y desbloqueo (ADM-06)."""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import FormView

from core import correo, navegacion
from cuentas import services
from cuentas.forms import FormularioCliente, FormularioClienteNuevo
from cuentas.models import EnlaceAcceso
from panel.views.base import VistaDeCliente, VistaDeUsuario

_TITULO_DEL_ENLACE = {
    EnlaceAcceso.Tipo.ACTIVACION: "Enlace de activación",
    EnlaceAcceso.Tipo.RESTABLECIMIENTO: "Enlace para definir una contraseña nueva",
}


def _mostrar_enlace(vista, cuenta, entrega, *, creada=False):
    """Página que muestra el enlace una sola vez. Es la respuesta directa del POST: el
    enlace no se guarda en la sesión ni en ninguna otra parte."""
    titulo = _TITULO_DEL_ENLACE[entrega.enlace.tipo]
    contexto = {
        **navegacion.contexto(vista.request.user, vista.seccion),
        **vista.contexto_de_ficha(),
    }
    contexto.update(
        cuenta=cuenta,
        entrega=entrega,
        creada=creada,
        titulo=titulo,
        url_usuarios=vista.url_ficha("usuarios"),
        migas=[*contexto["migas"], ("Usuarios", vista.url_ficha("usuarios")), (titulo, "")],
    )
    return render(vista.request, "panel/usuario_enlace.html", contexto)


class UsuarioNuevo(VistaDeCliente, FormView):
    template_name = "panel/usuario_formulario.html"
    form_class = FormularioClienteNuevo
    pestana = "usuarios"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "correo_configurado": correo.correo_configurado()}

    def form_valid(self, form):
        datos = form.cleaned_data
        cuenta = services.crear_cliente(
            self.empresa,
            rut=datos["rut"],
            nombre=datos["nombre"],
            email=datos["email"],
            actor=self.request.user,
            request=self.request,
        )
        entrega = services.entregar_enlace(
            cuenta,
            por_correo=datos.get("por_correo", False),
            actor=self.request.user,
            request=self.request,
        )
        if entrega is None:
            messages.warning(
                self.request,
                f"Se creó la cuenta de {cuenta.nombre}, pero el cliente está inactivo: "
                "reactívelo para generar el enlace de activación.",
            )
            return redirect(self.url_ficha("usuarios"))
        return _mostrar_enlace(self, cuenta, entrega, creada=True)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["migas"] = [
            *contexto["migas"],
            ("Usuarios", self.url_ficha("usuarios")),
            ("Nuevo usuario", ""),
        ]
        contexto["correo_configurado"] = correo.correo_configurado()
        return contexto


class UsuarioEditar(VistaDeUsuario, FormView):
    template_name = "panel/usuario_formulario.html"
    form_class = FormularioCliente

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "usuario": self.cuenta}

    def form_valid(self, form):
        datos = form.cleaned_data
        if services.editar_cliente(
            self.cuenta,
            rut=datos["rut"],
            nombre=datos["nombre"],
            email=datos["email"],
            actor=self.request.user,
            request=self.request,
        ):
            messages.success(self.request, f"Se guardaron los cambios de {self.cuenta.nombre}.")
        return redirect(self.url_ficha("usuarios"))

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["cuenta"] = self.cuenta
        contexto["migas"] = [
            *contexto["migas"],
            ("Usuarios", self.url_ficha("usuarios")),
            ("Editar usuario", ""),
        ]
        return contexto


class UsuarioEstado(VistaDeUsuario, View):
    """Desactiva o reactiva la cuenta. Solo POST, tras el diálogo de confirmación."""

    http_method_names = ["post"]

    def post(self, request, **kwargs):
        activo = request.POST.get("activo") == "si"
        if services.cambiar_estado_cliente(
            self.cuenta, activo, actor=request.user, request=request
        ):
            if activo:
                messages.success(request, f"Se reactivó la cuenta de {self.cuenta.nombre}.")
            else:
                messages.success(
                    request,
                    f"Se desactivó la cuenta de {self.cuenta.nombre}: ya no puede ingresar.",
                )
        return redirect(self.url_ficha("usuarios"))


class UsuarioEnlace(VistaDeUsuario, View):
    """Genera un enlace nuevo (el anterior deja de servir) y lo muestra para copiarlo."""

    http_method_names = ["post"]

    def post(self, request, **kwargs):
        entrega = services.entregar_enlace(
            self.cuenta,
            por_correo=request.POST.get("por_correo") == "si" and correo.correo_configurado(),
            actor=request.user,
            request=request,
        )
        if entrega is None:
            messages.error(
                request,
                "No se generó el enlace: la cuenta o su cliente están inactivos. "
                "Reactívelos primero.",
            )
            return redirect(self.url_ficha("usuarios"))
        return _mostrar_enlace(self, self.cuenta, entrega)


class UsuarioDesbloquear(VistaDeUsuario, View):
    """Desbloqueo manual tras intentos fallidos (AUT-04)."""

    http_method_names = ["post"]

    def post(self, request, **kwargs):
        services.desbloquear(self.cuenta, actor=request.user, request=request)
        messages.success(request, f"Se desbloqueó el acceso de {self.cuenta.nombre}.")
        return redirect(self.url_ficha("usuarios"))
