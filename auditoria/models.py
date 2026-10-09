from django.conf import settings
from django.db import models
from django.utils import timezone


class SoloAgregar(Exception):
    """La auditoría no se edita ni se borra desde la aplicación (AUD-03)."""


class EventoQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise SoloAgregar("Los eventos de auditoría no se editan.")

    def delete(self):
        raise SoloAgregar("Los eventos de auditoría no se borran.")


class EventoAuditoria(models.Model):
    """Registro de un hecho relevante. Solo se agregan filas.

    No hereda de ModeloConFechas: `fecha` es su fecha de creación y, como la fila nunca
    cambia, una fecha de actualización no aportaría nada.
    """

    class Accion(models.TextChoices):
        ACCESO_EXITOSO = "acceso_exitoso", "Inicio de sesión"
        ACCESO_FALLIDO = "acceso_fallido", "Intento de acceso fallido"
        BLOQUEO = "bloqueo", "Bloqueo por intentos fallidos"
        DESBLOQUEO = "desbloqueo", "Desbloqueo manual"
        CIERRE_SESION = "cierre_sesion", "Cierre de sesión"
        USUARIO_CREADO = "usuario_creado", "Alta de usuario"
        ENLACE_GENERADO = "enlace_generado", "Enlace de acceso generado"
        ACTIVACION = "activacion", "Activación de cuenta"
        RECUPERACION_SOLICITADA = "recuperacion_solicitada", "Recuperación solicitada"
        RECUPERACION_CORREO = "recuperacion_correo", "Correo de recuperación"
        RESTABLECIMIENTO = "restablecimiento", "Contraseña restablecida"
        CAMBIO_CONTRASENA = "cambio_contrasena", "Cambio de contraseña"
        DOS_FACTORES_ENROLADO = "2fa_enrolado", "2FA configurado"
        DOS_FACTORES_VERIFICADO = "2fa_verificado", "2FA verificado"
        DOS_FACTORES_FALLIDO = "2fa_fallido", "Código 2FA incorrecto"
        DOS_FACTORES_RECUPERACION = "2fa_recuperacion", "Código de recuperación 2FA usado"
        DOS_FACTORES_RESTABLECIDO = "2fa_restablecido", "2FA restablecido"

    fecha = models.DateTimeField("fecha", default=timezone.now, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="actor",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    # Solo se guarda si lo escrito es un RUT válido: en ese campo alguien podría
    # escribir su contraseña por error.
    rut_intentado = models.CharField("RUT intentado", max_length=9, blank=True)
    accion = models.CharField("acción", max_length=30, choices=Accion.choices)
    empresa = models.ForeignKey(
        "empresas.Empresa",
        verbose_name="empresa",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    objeto_tipo = models.CharField("tipo de objeto", max_length=30, blank=True)
    objeto_uuid = models.UUIDField("UUID del objeto", null=True, blank=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    detalle = models.CharField("detalle", max_length=200, blank=True)

    objects = EventoQuerySet.as_manager()

    class Meta:
        verbose_name = "evento de auditoría"
        verbose_name_plural = "eventos de auditoría"
        ordering = ["-fecha", "-id"]
        indexes = [
            models.Index(fields=["-fecha"], name="evento_fecha_idx"),
            models.Index(fields=["empresa", "-fecha"], name="evento_empresa_fecha_idx"),
            models.Index(fields=["accion", "-fecha"], name="evento_accion_fecha_idx"),
            models.Index(fields=["actor", "-fecha"], name="evento_actor_fecha_idx"),
        ]

    def __str__(self):
        return f"{self.get_accion_display()} ({self.fecha:%d-%m-%Y %H:%M})"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise SoloAgregar("Los eventos de auditoría no se editan.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise SoloAgregar("Los eventos de auditoría no se borran.")
