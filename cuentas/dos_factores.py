"""Segundo factor de los administradores: TOTP y códigos de recuperación (AUT-10)."""

import re
import time
from base64 import b32encode
from dataclasses import dataclass

import django_otp
import segno
from django.conf import settings
from django.db import transaction
from django.utils.safestring import mark_safe
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from auditoria.services import Accion, registrar

NOMBRE_TOTP = "Aplicación de autenticación"
NOMBRE_CODIGOS = "Códigos de recuperación"
CANTIDAD_DE_CODIGOS = 10

_PERMISO = "enrolamiento_2fa"
_DISPOSITIVO = "enrolamiento_2fa_dispositivo"
_CODIGOS = "enrolamiento_2fa_codigos"
_SEIS_DIGITOS = re.compile(r"^\d{6}$")


def esta_verificado(usuario):
    """True si la sesión actual ya pasó el segundo factor. Sin el middleware, nunca."""
    verificar = getattr(usuario, "is_verified", None)
    return bool(verificar and verificar())


def tiene_dispositivo(usuario):
    return django_otp.user_has_device(usuario, confirmed=True)


# --- Enrolamiento, ligado al uso de un enlace ----------------------------------------


def conceder_enrolamiento(request, usuario):
    """Marca la sesión que acaba de usar un enlace de activación o de restablecimiento.

    Solo esa sesión, y por un tiempo acotado, puede enrolar el 2FA. Quien entra solo con
    la contraseña de un administrador sin 2FA no puede registrar su propio dispositivo.
    """
    request.session[_PERMISO] = {
        "usuario": usuario.pk,
        "hasta": time.time() + settings.ENROLAMIENTO_2FA_MINUTOS * 60,
    }


def puede_enrolar(request):
    permiso = request.session.get(_PERMISO)
    return bool(
        permiso
        and permiso.get("usuario") == request.user.pk
        and permiso.get("hasta", 0) > time.time()
        and not tiene_dispositivo(request.user)
    )


def dispositivo_pendiente(request):
    """Dispositivo TOTP sin confirmar de esta sesión; lo crea si hace falta.

    Uno que haya quedado a medias en otra sesión se descarta: su clave ya se mostró.
    """
    usuario = request.user
    pendientes = TOTPDevice.objects.filter(user=usuario, confirmed=False)
    dispositivo = pendientes.filter(pk=request.session.get(_DISPOSITIVO)).first()
    if dispositivo is None:
        pendientes.delete()
        dispositivo = TOTPDevice.objects.create(user=usuario, name=NOMBRE_TOTP, confirmed=False)
        request.session[_DISPOSITIVO] = dispositivo.pk
    return dispositivo


def clave_manual(dispositivo):
    """La clave en base32, en grupos de cuatro, para escribirla a mano en la aplicación."""
    clave = b32encode(dispositivo.bin_key).decode()
    return " ".join(clave[i : i + 4] for i in range(0, len(clave), 4))


def qr_svg(dispositivo):
    """Código QR como SVG incrustado: sin servicios externos y compatible con la CSP.

    El SVG lo genera segno solo con trazos; no incluye texto ni datos de formularios.
    """
    codigo = segno.make(dispositivo.config_url, error="m")
    return mark_safe(
        codigo.svg_inline(scale=4, border=2, dark="#0f172a", svgclass="qr", lineclass=None)
    )


def confirmar_enrolamiento(request, codigo):
    """Confirma el dispositivo con un código. Devuelve True si quedó enrolado.

    Los códigos de recuperación quedan en la sesión para mostrarlos una sola vez.
    """
    if not puede_enrolar(request):
        return False
    usuario = request.user
    with transaction.atomic():
        dispositivo = (
            TOTPDevice.objects.select_for_update()
            .filter(user=usuario, confirmed=False, pk=request.session.get(_DISPOSITIVO))
            .first()
        )
        if dispositivo is None or not dispositivo.verify_token(_limpiar(codigo)):
            return False
        dispositivo.confirmed = True
        dispositivo.save(update_fields=["confirmed"])
        StaticDevice.objects.filter(user=usuario).delete()
        recuperacion = StaticDevice.objects.create(user=usuario, name=NOMBRE_CODIGOS)
        codigos = [StaticToken.random_token() for _ in range(CANTIDAD_DE_CODIGOS)]
        StaticToken.objects.bulk_create(
            StaticToken(device=recuperacion, token=valor) for valor in codigos
        )
    django_otp.login(request, dispositivo)
    del request.session[_PERMISO]
    request.session.pop(_DISPOSITIVO, None)
    request.session[_CODIGOS] = codigos
    registrar(Accion.DOS_FACTORES_ENROLADO, request=request, actor=usuario, objeto=usuario)
    return True


def codigos_de_recuperacion_por_guardar(request):
    """Los códigos recién generados, mientras la persona no confirme que los guardó."""
    return request.session.get(_CODIGOS)


def olvidar_codigos_de_recuperacion(request):
    """La persona confirmó que los guardó: salen de la sesión y no se vuelven a mostrar."""
    request.session.pop(_CODIGOS, None)


# --- Verificación en cada inicio de sesión -------------------------------------------


@dataclass
class ResultadoVerificacion:
    aceptado: bool = False
    en_espera: bool = False
    codigos_restantes: int | None = None


def _limpiar(codigo):
    return re.sub(r"[\s-]", "", codigo or "").lower()


def verificar(request, codigo):
    """Comprueba un código TOTP o uno de recuperación y marca la sesión como verificada."""
    usuario = request.user
    codigo = _limpiar(codigo)
    # El formato decide el dispositivo: un código de recuperación no suma fallos al TOTP.
    modelo = TOTPDevice if _SEIS_DIGITOS.match(codigo) else StaticDevice
    resultado = ResultadoVerificacion()
    with transaction.atomic():
        dispositivo = (
            modelo.objects.select_for_update().filter(user=usuario, confirmed=True).first()
        )
        if dispositivo is None:
            pass
        elif not dispositivo.verify_is_allowed()[0]:
            resultado.en_espera = True
        elif dispositivo.verify_token(codigo):
            resultado.aceptado = True
            if modelo is StaticDevice:
                resultado.codigos_restantes = dispositivo.token_set.count()

    if not resultado.aceptado:
        registrar(
            Accion.DOS_FACTORES_FALLIDO,
            request=request,
            actor=usuario,
            detalle="En espera por intentos fallidos" if resultado.en_espera else "",
        )
        return resultado

    django_otp.login(request, dispositivo)
    if modelo is StaticDevice:
        registrar(
            Accion.DOS_FACTORES_RECUPERACION,
            request=request,
            actor=usuario,
            detalle=f"Quedan {resultado.codigos_restantes}",
        )
    else:
        registrar(Accion.DOS_FACTORES_VERIFICADO, request=request, actor=usuario)
    return resultado


def restablecer(usuario):
    """Elimina todos los dispositivos del usuario. Devuelve cuántos tenía."""
    cantidad = 0
    for modelo in (TOTPDevice, StaticDevice):
        cantidad += modelo.objects.filter(user=usuario).delete()[0]
    return cantidad
