"""Lógica de acceso, enlaces de un solo uso y recuperación (AUT-01 a AUT-08)."""

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from auditoria.services import Accion, registrar
from core import correo, limites, tareas
from core import rut as utilidades_rut
from cuentas import bloqueo
from cuentas.backends import verificacion_de_relleno
from cuentas.models import EnlaceAcceso, Usuario

logger = logging.getLogger(__name__)

BACKEND = "cuentas.backends.BackendRut"

_VIGENCIA = {
    EnlaceAcceso.Tipo.ACTIVACION: lambda: timedelta(hours=settings.ENLACE_ACTIVACION_HORAS),
    EnlaceAcceso.Tipo.RESTABLECIMIENTO: lambda: timedelta(
        minutes=settings.ENLACE_RESTABLECIMIENTO_MINUTOS
    ),
}
_RUTA = {
    EnlaceAcceso.Tipo.ACTIVACION: "cuentas:activar",
    EnlaceAcceso.Tipo.RESTABLECIMIENTO: "cuentas:restablecer",
}
_ACCION_AL_USAR = {
    EnlaceAcceso.Tipo.ACTIVACION: Accion.ACTIVACION,
    EnlaceAcceso.Tipo.RESTABLECIMIENTO: Accion.RESTABLECIMIENTO,
}


# --- Acceso ---------------------------------------------------------------------------


@dataclass
class ResultadoAcceso:
    usuario: Usuario | None = None
    bloqueado: bool = False


@sensitive_variables("contrasena")
def intentar_acceso(request, rut_ingresado, contrasena):
    """Evalúa un intento de acceso y, si es correcto, inicia la sesión.

    Todos los caminos de fallo hacen el mismo trabajo: una verificación de contraseña,
    un evento de auditoría y la cuenta de intentos. Lo que varía es solo el resultado.
    """
    ip = request.ip_cliente
    rut = (
        utilidades_rut.normalizar(rut_ingresado) if utilidades_rut.es_valido(rut_ingresado) else ""
    )

    if bloqueo.esta_bloqueado(rut, ip):
        # Ni siquiera la contraseña correcta entra durante el bloqueo.
        verificacion_de_relleno(contrasena)
        return ResultadoAcceso(bloqueado=True)

    usuario = authenticate(request, rut=rut_ingresado, password=contrasena)
    if usuario is None:
        cuenta = getattr(request, "cuenta_intentada", None)
        registrar(
            Accion.ACCESO_FALLIDO,
            request=request,
            rut_intentado=rut,
            empresa=cuenta.empresa if cuenta else None,
        )
        motivo = bloqueo.registrar_fallo(rut, ip)
        if motivo:
            registrar(
                Accion.BLOQUEO,
                request=request,
                rut_intentado=rut,
                empresa=cuenta.empresa if cuenta else None,
                detalle="Por RUT e IP" if motivo == bloqueo.MOTIVO_RUT_IP else "Por IP",
            )
            logger.warning("Bloqueo de acceso activado (%s)", motivo)
        return ResultadoAcceso()

    bloqueo.limpiar(rut, ip)
    login(request, usuario)
    registrar(Accion.ACCESO_EXITOSO, request=request, actor=usuario)
    return ResultadoAcceso(usuario=usuario)


def cerrar_sesion(request):
    if request.user.is_authenticated:
        registrar(Accion.CIERRE_SESION, request=request, actor=request.user)
    logout(request)


def desbloquear(usuario, *, actor=None, request=None):
    """Desbloqueo manual de un RUT, desde cualquier IP (AUT-04)."""
    bloqueo.desbloquear_rut(usuario.rut)
    registrar(
        Accion.DESBLOQUEO, request=request, actor=actor, empresa=usuario.empresa, objeto=usuario
    )


# --- Enlaces de un solo uso -----------------------------------------------------------


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def url_del_enlace(tipo, token):
    """URL absoluta, armada con SITIO_URL y nunca con el encabezado Host de la petición."""
    return settings.SITIO_URL.rstrip("/") + reverse(_RUTA[tipo], args=[token])


def generar_enlace(usuario, tipo, *, creado_por=None, request=None, envio=""):
    """Crea un enlace nuevo y revoca los anteriores del usuario. Devuelve (enlace, token).

    El token solo existe en la memoria de quien llama: en la base queda su hash.
    """
    token = secrets.token_urlsafe(32)
    ahora = timezone.now()
    with transaction.atomic():
        usuario.enlaces.filter(usado_en__isnull=True, revocado_en__isnull=True).update(
            revocado_en=ahora
        )
        enlace = EnlaceAcceso.objects.create(
            usuario=usuario,
            tipo=tipo,
            token_hash=_hash(token),
            expira_en=ahora + _VIGENCIA[tipo](),
            creado_por=creado_por,
            envio=envio,
        )
    registrar(
        Accion.ENLACE_GENERADO,
        request=request,
        actor=creado_por,
        empresa=usuario.empresa,
        objeto=usuario,
        detalle=enlace.get_tipo_display(),
    )
    return enlace, token


def enlace_vigente(tipo, token):
    """Devuelve el enlace si es de ese tipo, no se usó, no venció y su cuenta sigue activa."""
    enlace = (
        EnlaceAcceso.objects.select_related("usuario__empresa")
        .filter(token_hash=_hash(token), tipo=tipo)
        .first()
    )
    if enlace is None or not enlace.esta_vigente(timezone.now()):
        return None
    return enlace


@sensitive_variables("contrasena")
def usar_enlace(request, tipo, token, contrasena):
    """Define la contraseña con el enlace y lo consume. Devuelve el usuario, o None si no vale.

    La fila se bloquea dentro de la transacción: dos usos simultáneos no pueden pasar ambos.
    """
    ahora = timezone.now()
    with transaction.atomic():
        enlace = (
            EnlaceAcceso.objects.select_for_update(of=("self",))
            .select_related("usuario__empresa")
            .filter(token_hash=_hash(token), tipo=tipo)
            .first()
        )
        if enlace is None or not enlace.esta_vigente(ahora):
            return None
        usuario = enlace.usuario
        usuario.set_password(contrasena)
        usuario.save(update_fields=["password", "actualizado_en"])
        enlace.usado_en = ahora
        enlace.save(update_fields=["usado_en", "actualizado_en"])
        usuario.enlaces.filter(usado_en__isnull=True, revocado_en__isnull=True).update(
            revocado_en=ahora
        )
    # Con la contraseña nueva, las sesiones abiertas con la anterior dejan de valer (AUT-08).
    bloqueo.desbloquear_rut(usuario.rut)
    login(request, usuario, backend=BACKEND)
    registrar(_ACCION_AL_USAR[tipo], request=request, actor=usuario, objeto=usuario)
    return usuario


@sensitive_variables("formulario")
def cambiar_contrasena(request, formulario):
    """Guarda la contraseña nueva; la sesión actual sigue y las demás se cierran (AUT-08)."""
    usuario = formulario.save()
    update_session_auth_hash(request, usuario)
    registrar(Accion.CAMBIO_CONTRASENA, request=request, actor=usuario, objeto=usuario)


# --- Recuperación ---------------------------------------------------------------------


def solicitar_recuperacion(request, rut_ingresado):
    """Atiende una solicitud de recuperación sin revelar si la cuenta existe (AUT-07).

    En la petición se hace siempre lo mismo. Crear el enlace y hablar con el servidor de
    correo ocurre después, fuera de la petición, y solo si la cuenta califica.
    """
    rut = utilidades_rut.normalizar(rut_ingresado)
    ip = request.ip_cliente
    una_hora = 3600
    # Se cuentan siempre los dos, para que el trabajo no dependa del resultado.
    por_ip = limites.contar(f"recuperar:ip:{ip}", una_hora)
    por_rut = limites.contar(f"recuperar:rut:{rut}", una_hora)
    dentro_del_limite = (
        por_ip <= settings.RECUPERACION_MAXIMO_POR_IP
        and por_rut <= settings.RECUPERACION_MAXIMO_POR_RUT
    )

    usuario = Usuario.objects.select_related("empresa").filter(rut=rut).first()
    califica = bool(usuario and usuario.puede_acceder and usuario.email)
    registrar(
        Accion.RECUPERACION_SOLICITADA,
        request=request,
        rut_intentado=rut,
        detalle="" if dentro_del_limite else "Sobre el límite de solicitudes",
    )
    tareas.en_segundo_plano(
        enviar_enlace_de_recuperacion, usuario.pk if califica and dentro_del_limite else None, ip
    )


def enviar_enlace_de_recuperacion(usuario_id, ip):
    """Crea el enlace y lo envía. El resultado queda en el enlace, el log y la auditoría."""
    if usuario_id is None:
        return
    usuario = Usuario.objects.select_related("empresa").filter(pk=usuario_id).first()
    if usuario is None or not usuario.puede_acceder or not usuario.email:
        return
    # Nace como "pendiente": si el proceso se cae antes de terminar, queda como no enviado.
    enlace, token = generar_enlace(
        usuario, EnlaceAcceso.Tipo.RESTABLECIMIENTO, envio=EnlaceAcceso.Envio.PENDIENTE
    )
    cuerpo = render_to_string(
        "cuentas/correo/recuperacion.txt",
        {
            "nombre": usuario.nombre,
            "url": url_del_enlace(enlace.tipo, token),
            "minutos": settings.ENLACE_RESTABLECIMIENTO_MINUTOS,
        },
    )
    resultado, error = correo.enviar("Restablecer su contraseña", cuerpo, [usuario.email])
    EnlaceAcceso.objects.filter(pk=enlace.pk).update(envio=resultado, envio_error=error)
    registrar(
        Accion.RECUPERACION_CORREO,
        empresa=usuario.empresa,
        objeto=usuario,
        ip=ip,
        detalle=resultado.label,
    )
    if resultado == correo.Resultado.ENVIADA:
        logger.info("Correo de recuperación enviado")
    else:
        logger.warning("Correo de recuperación no enviado: %s", resultado.label)
