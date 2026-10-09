from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import FormView

from core import limites, navegacion
from core.mixins import CuentaMixin
from cuentas import dos_factores, services
from cuentas.forms import (
    FormularioAcceso,
    FormularioCambiarContrasena,
    FormularioCodigo,
    FormularioDefinirContrasena,
    FormularioRecuperacion,
    FormularioVerificacion,
)
from cuentas.models import EnlaceAcceso

MENSAJE_CREDENCIALES = "RUT o contraseña incorrectos."
MENSAJE_BLOQUEO = "Demasiados intentos. Espere unos minutos e intente nuevamente."
MENSAJE_CODIGO = "El código no es correcto."
MENSAJE_ESPERA = "Demasiados intentos. Espere un momento antes de ingresar otro código."

_TEXTOS_ENLACE = {
    EnlaceAcceso.Tipo.ACTIVACION: {
        "titulo": "Active su cuenta",
        "bajada": "Defina la contraseña con la que ingresará al portal.",
        "boton": "Activar cuenta",
        "exito": "Su cuenta quedó activada.",
    },
    EnlaceAcceso.Tipo.RESTABLECIMIENTO: {
        "titulo": "Restablezca su contraseña",
        "bajada": "Defina una contraseña nueva para su cuenta.",
        "boton": "Guardar contraseña",
        "exito": "Su contraseña quedó restablecida.",
    },
}


def _destino_pedido(request):
    """El destino indicado en `next`, solo si apunta a esta misma aplicación."""
    destino = request.POST.get(REDIRECT_FIELD_NAME) or request.GET.get(REDIRECT_FIELD_NAME) or ""
    if url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return destino
    return ""


def _continuar(request, usuario):
    """Redirección según el rol (AUT-03): el administrador pasa antes por el segundo factor."""
    destino = _destino_pedido(request)
    if usuario.es_administrador and not dos_factores.esta_verificado(usuario):
        return redirect_to_login(
            destino or reverse("panel:inicio"), login_url=reverse("cuentas:verificacion")
        )
    return redirect(destino or navegacion.inicio_de(usuario))


def _requiere_administrador_con_sesion(request):
    """Las pantallas del segundo factor son de administradores que ya pasaron la contraseña."""
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    if not request.user.es_administrador:
        raise Http404
    return None


# --- Acceso y cierre de sesión ---------------------------------------------------------


@sensitive_post_parameters("contrasena")
@never_cache
@require_http_methods(["GET", "POST"])
def acceso(request):
    if request.user.is_authenticated:
        return _continuar(request, request.user)

    formulario = FormularioAcceso(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        resultado = services.intentar_acceso(
            request, formulario.cleaned_data["rut"], formulario.cleaned_data["contrasena"]
        )
        if resultado.usuario is not None:
            return _continuar(request, resultado.usuario)
        formulario.add_error(None, MENSAJE_BLOQUEO if resultado.bloqueado else MENSAJE_CREDENCIALES)
    return render(
        request,
        "cuentas/acceso.html",
        {"formulario": formulario, "destino": _destino_pedido(request)},
    )


@require_POST
def salir(request):
    services.cerrar_sesion(request)
    return redirect("cuentas:acceso")


# --- Segundo factor --------------------------------------------------------------------


@never_cache
@require_http_methods(["GET", "POST"])
def verificacion(request):
    rechazo = _requiere_administrador_con_sesion(request)
    if rechazo:
        return rechazo
    destino = _destino_pedido(request)
    if dos_factores.esta_verificado(request.user):
        return redirect(destino or "panel:inicio")
    if not dos_factores.tiene_dispositivo(request.user):
        return redirect("cuentas:configurar_2fa")

    formulario = FormularioVerificacion(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        resultado = dos_factores.verificar(request, formulario.cleaned_data["codigo"])
        if resultado.aceptado:
            if resultado.codigos_restantes is not None:
                messages.warning(
                    request,
                    "Usó un código de recuperación. "
                    f"Le quedan {resultado.codigos_restantes} sin usar.",
                )
            return redirect(destino or "panel:inicio")
        formulario.add_error(None, MENSAJE_ESPERA if resultado.en_espera else MENSAJE_CODIGO)
    return render(
        request, "cuentas/verificacion.html", {"formulario": formulario, "destino": destino}
    )


@never_cache
@require_http_methods(["GET", "POST"])
def configurar_2fa(request):
    rechazo = _requiere_administrador_con_sesion(request)
    if rechazo:
        return rechazo
    if dos_factores.tiene_dispositivo(request.user):
        return redirect("cuentas:verificacion")
    if not dos_factores.puede_enrolar(request):
        # Entró solo con la contraseña: no puede registrar su propio dispositivo.
        return render(request, "cuentas/enlace_requerido.html", status=403)

    formulario = FormularioCodigo(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        if dos_factores.confirmar_enrolamiento(request, formulario.cleaned_data["codigo"]):
            return redirect("cuentas:codigos_2fa")
        formulario.add_error(None, MENSAJE_CODIGO)
    dispositivo = dos_factores.dispositivo_pendiente(request)
    return render(
        request,
        "cuentas/configurar_2fa.html",
        {
            "formulario": formulario,
            "qr": dos_factores.qr_svg(dispositivo),
            "clave": dos_factores.clave_manual(dispositivo),
        },
    )


@never_cache
@require_http_methods(["GET"])
def codigos_2fa(request):
    rechazo = _requiere_administrador_con_sesion(request)
    if rechazo:
        return rechazo
    codigos = dos_factores.tomar_codigos_de_recuperacion(request)
    if not codigos:
        # Se muestran una sola vez.
        return redirect("cuentas:verificacion")
    return render(request, "cuentas/codigos_2fa.html", {"codigos": codigos})


# --- Recuperación, activación y restablecimiento ---------------------------------------


@never_cache
@require_http_methods(["GET", "POST"])
def recuperar(request):
    formulario = FormularioRecuperacion(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        services.solicitar_recuperacion(request, formulario.cleaned_data["rut"])
        return redirect("cuentas:recuperar_enviado")
    return render(request, "cuentas/recuperar.html", {"formulario": formulario})


@never_cache
@require_http_methods(["GET"])
def recuperar_enviado(request):
    return render(request, "cuentas/recuperar_enviado.html")


@sensitive_post_parameters()
@never_cache
@require_http_methods(["GET", "POST"])
def definir_contrasena(request, token, tipo):
    """Activación y restablecimiento: mismo flujo, con otro enlace y otros textos.

    Abrir el enlace no lo consume (los filtros de correo los abren): se consume al
    guardar la contraseña.
    """
    enlace = services.enlace_vigente(tipo, token)
    if enlace is None:
        return render(request, "cuentas/enlace_invalido.html", status=404)

    formulario = FormularioDefinirContrasena(enlace.usuario, request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        usuario = services.usar_enlace(
            request, tipo, token, formulario.cleaned_data["new_password1"]
        )
        if usuario is None:
            return render(request, "cuentas/enlace_invalido.html", status=404)
        if usuario.es_administrador:
            dos_factores.conceder_enrolamiento(request, usuario)
        messages.success(request, _TEXTOS_ENLACE[tipo]["exito"])
        return _continuar(request, usuario)
    return render(
        request,
        "cuentas/definir_contrasena.html",
        {"formulario": formulario, "textos": _TEXTOS_ENLACE[tipo]},
    )


# --- Mi cuenta -------------------------------------------------------------------------


class MiCuenta(CuentaMixin, FormView):
    """Datos de la cuenta, de solo lectura, y cambio de contraseña (AUT-08).

    El RUT y el correo no se editan aquí: el correo es por donde llega la recuperación
    y solo lo cambia un administrador.
    """

    template_name = "cuentas/mi_cuenta.html"
    form_class = FormularioCambiarContrasena
    success_url = reverse_lazy("cuentas:mi_cuenta")
    seccion = "cuenta"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def form_valid(self, form):
        services.cambiar_contrasena(self.request, form)
        messages.success(
            self.request,
            "Su contraseña quedó cambiada. Las demás sesiones abiertas se cerraron.",
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        # Quien tenga una sesión ajena no puede usar este formulario para adivinar la
        # contraseña actual: tras varios fallos seguidos, la sesión se cierra.
        if form.has_error("old_password"):
            clave = f"cuenta:clave:{self.request.user.pk}"
            ventana = settings.ACCESO_VENTANA_MINUTOS * 60
            if limites.contar(clave, ventana) >= settings.ACCESO_INTENTOS_MAXIMOS:
                limites.reiniciar(clave)
                services.cerrar_sesion(self.request)
                messages.error(self.request, MENSAJE_BLOQUEO)
                return redirect("cuentas:acceso")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["minutos_de_sesion"] = settings.SESSION_COOKIE_AGE // 60
        return contexto
