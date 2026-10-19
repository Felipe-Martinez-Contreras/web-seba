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

    def filtrar(self, *, empresa=None, rut="", accion="", desde=None, hasta=None):
        """Filtros del listado (ADM-11). El RUT busca al actor y también el RUT intentado."""
        eventos = self
        if empresa is not None:
            eventos = eventos.filter(empresa=empresa)
        if rut:
            eventos = eventos.filter(models.Q(actor__rut=rut) | models.Q(rut_intentado=rut))
        if accion:
            eventos = eventos.filter(accion=accion)
        if desde:
            eventos = eventos.filter(fecha__date__gte=desde)
        if hasta:
            eventos = eventos.filter(fecha__date__lte=hasta)
        return eventos

    def depurar(self, antes_de):
        """Borra los eventos anteriores a la fecha y devuelve cuántos eran.

        Es el único borrado que existe: el de la retención (AUD-03), y solo lo usa el
        comando `depurar_auditoria`, que requiere acceso al servidor.
        """
        return models.QuerySet.delete(self.filter(fecha__lt=antes_de))[0]


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
        ENLACE_CORREO = "enlace_correo", "Correo con enlace de acceso"
        USUARIO_EDITADO = "usuario_editado", "Usuario editado"
        USUARIO_DESACTIVADO = "usuario_desactivado", "Usuario desactivado"
        USUARIO_REACTIVADO = "usuario_reactivado", "Usuario reactivado"
        EMPRESA_CREADA = "empresa_creada", "Alta de cliente"
        EMPRESA_EDITADA = "empresa_editada", "Cliente editado"
        EMPRESA_DESACTIVADA = "empresa_desactivada", "Cliente desactivado"
        EMPRESA_REACTIVADA = "empresa_reactivada", "Cliente reactivado"
        CARPETA_CREADA = "carpeta_creada", "Carpeta creada"
        CARPETA_EDITADA = "carpeta_editada", "Carpeta editada"
        CARPETA_ELIMINADA = "carpeta_eliminada", "Carpeta eliminada"
        DOCUMENTO_SUBIDO = "documento_subido", "Documento subido"
        DOCUMENTO_REEMPLAZADO = "documento_reemplazado", "Documento reemplazado"
        DOCUMENTO_EDITADO = "documento_editado", "Documento editado"
        DOCUMENTO_MOVIDO = "documento_movido", "Documento movido"
        DOCUMENTO_ELIMINADO = "documento_eliminado", "Documento enviado a la papelera"
        DOCUMENTO_RESTAURADO = "documento_restaurado", "Documento restaurado"
        DOCUMENTO_PURGADO = "documento_purgado", "Documento borrado definitivamente"
        DOCUMENTO_VISTO = "documento_visto", "Documento visto en pantalla"
        DOCUMENTO_DESCARGADO = "documento_descargado", "Documento descargado"
        AUDITORIA_DEPURADA = "auditoria_depurada", "Depuración de la auditoría"
        SOLICITUD_ESTADO = "solicitud_estado", "Cambio de estado de solicitud"
        SOLICITUD_REINTENTO = "solicitud_reintento", "Reintento de notificación de solicitud"
        SOLICITUDES_DEPURADAS = "solicitudes_depuradas", "Depuración de solicitudes"
        IMAGEN_CAMBIADA = "imagen_cambiada", "Imagen del sitio cambiada"
        IMAGEN_RESTAURADA = "imagen_restaurada", "Imagen del sitio restaurada"
        RUBRO_CREADO = "rubro_creado", "Rubro creado"
        RUBRO_EDITADO = "rubro_editado", "Rubro editado"
        RUBRO_ELIMINADO = "rubro_eliminado", "Rubro eliminado"
        RUBRO_FOTO_CAMBIADA = "rubro_foto_cambiada", "Foto de rubro cambiada"

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
