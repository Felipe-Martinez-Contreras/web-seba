from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import UNUSABLE_PASSWORD_PREFIX, check_password
from django.views.decorators.debug import sensitive_variables

from core import rut as utilidades_rut
from cuentas.models import Usuario


def verificacion_de_relleno(contrasena):
    """Ejecuta el hasher una vez sin comparar con ninguna cuenta.

    Así un intento que no llega a evaluar una contraseña real (cuenta inexistente,
    inactiva, sin activar, RUT inválido o bloqueo vigente) tarda lo mismo que uno que sí.
    """
    check_password(contrasena, UNUSABLE_PASSWORD_PREFIX)


class BackendRut(ModelBackend):
    """Autenticación por RUT y contraseña.

    Todo intento ejecuta exactamente una verificación de contraseña, exista o no la
    cuenta (AUT-02), y `get_user` vuelve a comprobar en cada petición que la cuenta y
    su empresa sigan activas (AUT-11).
    """

    @sensitive_variables("password")
    def authenticate(self, request, username=None, password=None, **kwargs):
        rut = kwargs.get(Usuario.USERNAME_FIELD, username)
        if rut is None or password is None:
            return None
        usuario = None
        if utilidades_rut.es_valido(rut):
            usuario = Usuario.objects.select_related("empresa").filter(rut=rut).first()
        if request is not None:
            # Para la auditoría del intento; no se usa para decidir nada.
            request.cuenta_intentada = usuario
        if usuario is None or not self.user_can_authenticate(usuario):
            verificacion_de_relleno(password)
            return None
        # Con contraseña no utilizable (cuenta sin activar), check_password también
        # ejecuta el hasher una vez antes de responder que no coincide.
        return usuario if usuario.check_password(password) else None

    def user_can_authenticate(self, user):
        return user.puede_acceder

    def get_user(self, user_id):
        usuario = Usuario.objects.select_related("empresa").filter(pk=user_id).first()
        if usuario is None or not self.user_can_authenticate(usuario):
            return None
        return usuario
