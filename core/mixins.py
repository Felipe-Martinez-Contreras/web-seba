"""Mixins de rol: único punto de entrada de las vistas privadas (sección 5, SEG-04).

Toda vista del portal, del panel o de la cuenta hereda de uno de ellos. La regla se
aplica en el servidor, antes de ejecutar cualquier método de la vista.
"""

from django.contrib.auth.views import redirect_to_login
from django.http import Http404
from django.urls import reverse
from django.utils.cache import add_never_cache_headers

from core import navegacion

CLIENTE = "cliente"
ADMINISTRADOR = "administrador"


def _verificado(usuario):
    # Sin el middleware de 2FA el atributo no existe: en ese caso nadie está verificado.
    verificar = getattr(usuario, "is_verified", None)
    return bool(verificar and verificar())


class _VistaPrivada:
    roles = ()
    seccion = ""

    def dispatch(self, request, *args, **kwargs):
        usuario = request.user
        if not usuario.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if usuario.rol not in self.roles:
            # 404 y no 403: no se confirma que la dirección exista.
            raise Http404
        if usuario.rol == ADMINISTRADOR and not _verificado(usuario):
            return redirect_to_login(
                request.get_full_path(), login_url=reverse("cuentas:verificacion")
            )
        respuesta = super().dispatch(request, *args, **kwargs)
        add_never_cache_headers(respuesta)
        return respuesta

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(navegacion.contexto(self.request.user, self.seccion))
        return contexto


class ClienteMixin(_VistaPrivada):
    """Solo clientes. La cuenta y su empresa activas las garantiza el backend en cada petición."""

    roles = (CLIENTE,)


class AdministradorMixin(_VistaPrivada):
    """Solo administradores con el segundo factor verificado en esta sesión."""

    roles = (ADMINISTRADOR,)


class CuentaMixin(_VistaPrivada):
    """Cualquier usuario con sesión; al administrador se le exige además el segundo factor."""

    roles = (CLIENTE, ADMINISTRADOR)
