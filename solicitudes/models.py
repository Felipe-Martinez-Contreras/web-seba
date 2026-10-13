import datetime
import uuid

from django.db import models
from django.db.models import Q

from core.models import ModeloConFechas

# Una notificación "por enviar" más vieja que esto perdió su hilo (por ejemplo, por un
# reinicio del proceso) y la retoma `reintentar_notificaciones`.
ESPERA_DEL_HILO = datetime.timedelta(minutes=5)
OTRO_SERVICIO = "Otro / no estoy seguro"
# Menos que esto borraría solicitudes que todavía se están atendiendo: es un error de
# configuración, no un plazo.
RETENCION_MINIMA_DIAS = 30


class SolicitudQuerySet(models.QuerySet):
    def buscar(self, texto):
        """Por nombre, email o empresa (SOL-09)."""
        texto = (texto or "").strip()
        if not texto:
            return self
        return self.filter(
            Q(nombre__icontains=texto) | Q(email__icontains=texto) | Q(empresa__icontains=texto)
        )

    def filtrar(self, *, estado="", desde=None, hasta=None):
        solicitudes = self
        if estado:
            solicitudes = solicitudes.filter(estado=estado)
        if desde:
            solicitudes = solicitudes.filter(creado_en__date__gte=desde)
        if hasta:
            solicitudes = solicitudes.filter(creado_en__date__lte=hasta)
        return solicitudes

    def con_notificacion_fallida(self):
        return self.filter(notificacion=Solicitud.Notificacion.FALLIDA)

    def por_reintentar(self, *, maximo_intentos, ahora, correo_configurado):
        """Las que `reintentar_notificaciones` debe volver a intentar (SOL-11)."""
        condicion = Q(
            notificacion=Solicitud.Notificacion.FALLIDA, notificacion_intentos__lt=maximo_intentos
        ) | Q(notificacion=Solicitud.Notificacion.PENDIENTE, creado_en__lt=ahora - ESPERA_DEL_HILO)
        if correo_configurado:
            condicion |= Q(notificacion=Solicitud.Notificacion.NO_CONFIGURADA)
        return self.filter(condicion)

    def vencidas(self, *, ahora, dias):
        """Las que superaron el plazo de conservación, en cualquier estado."""
        return self.filter(creado_en__lt=ahora - datetime.timedelta(days=dias))


class Solicitud(ModeloConFechas):
    """Consulta o solicitud de cotización enviada desde el sitio público.

    No guarda la IP del visitante (sección 6). Una cotización es una solicitud de contacto:
    el sistema no calcula ni muestra precios (R6).
    """

    class Tipo(models.TextChoices):
        CONSULTA = "consulta", "Consulta"
        COTIZACION = "cotizacion", "Cotización"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_PROCESO = "en_proceso", "En proceso"
        RESUELTA = "resuelta", "Resuelta"
        DESCARTADA = "descartada", "Descartada"

    class Notificacion(models.TextChoices):
        # Transitorio: la solicitud ya está guardada y el correo aún no se intenta.
        PENDIENTE = "pendiente", "Por enviar"
        ENVIADA = "enviada", "Enviada"
        FALLIDA = "fallida", "Fallida"
        NO_CONFIGURADA = "no_configurada", "Correo no configurado"

    class Trabajadores(models.TextChoices):
        HASTA_10 = "1-10", "1 a 10"
        HASTA_25 = "11-25", "11 a 25"
        HASTA_100 = "26-100", "26 a 100"
        MAS_DE_100 = "101+", "Más de 100"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo = models.CharField("tipo", max_length=10, choices=Tipo.choices)
    nombre = models.CharField("nombre", max_length=150)
    email = models.EmailField("correo")
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    empresa = models.CharField("empresa", max_length=200, blank=True)
    # Vacío en una cotización significa "Otro / no estoy seguro".
    servicio = models.ForeignKey(
        "sitio.Servicio",
        verbose_name="servicio de interés",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="solicitudes",
    )
    trabajadores = models.CharField(
        "rango de trabajadores", max_length=10, choices=Trabajadores.choices, blank=True
    )
    comuna = models.CharField("comuna o región", max_length=100, blank=True)
    mensaje = models.TextField("mensaje")
    consentimiento = models.BooleanField("aceptó la política de privacidad")
    consentimiento_en = models.DateTimeField("fecha de la aceptación")
    estado = models.CharField(
        "estado", max_length=12, choices=Estado.choices, default=Estado.PENDIENTE
    )
    # Solo para administradores.
    notas_internas = models.TextField("notas internas", blank=True)
    notificacion = models.CharField(
        "estado de la notificación",
        max_length=15,
        choices=Notificacion.choices,
        default=Notificacion.PENDIENTE,
    )
    notificacion_error = models.CharField("error de la notificación", max_length=200, blank=True)
    notificacion_intentos = models.PositiveSmallIntegerField("intentos de notificación", default=0)
    notificada_en = models.DateTimeField("notificada en", null=True, blank=True)

    objects = SolicitudQuerySet.as_manager()

    class Meta:
        verbose_name = "solicitud"
        verbose_name_plural = "solicitudes"
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["tipo", "-creado_en"], name="solicitud_tipo_fecha_idx"),
            models.Index(fields=["tipo", "estado"], name="solicitud_tipo_estado_idx"),
            models.Index(fields=["notificacion"], name="solicitud_notificacion_idx"),
        ]
        constraints = [
            # Sin aceptación de la política no existe solicitud (SEG-12).
            models.CheckConstraint(
                condition=Q(consentimiento=True), name="solicitud_con_consentimiento"
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.nombre}"

    @property
    def tono_del_estado(self):
        """Tono de la insignia de seguimiento (sección 9). El estado siempre lleva texto."""
        return _TONO_DEL_ESTADO[self.estado]

    @property
    def tono_de_la_notificacion(self):
        return _TONO_DE_LA_NOTIFICACION[self.notificacion]

    @property
    def servicio_texto(self):
        """El servicio de interés como texto; solo tiene sentido en una cotización."""
        if self.servicio_id:
            return self.servicio.nombre
        return OTRO_SERVICIO if self.tipo == self.Tipo.COTIZACION else ""


_TONO_DEL_ESTADO = {
    Solicitud.Estado.PENDIENTE: "error",
    Solicitud.Estado.EN_PROCESO: "info",
    Solicitud.Estado.RESUELTA: "exito",
    Solicitud.Estado.DESCARTADA: "neutro",
}
_TONO_DE_LA_NOTIFICACION = {
    Solicitud.Notificacion.PENDIENTE: "neutro",
    Solicitud.Notificacion.ENVIADA: "exito",
    Solicitud.Notificacion.FALLIDA: "error",
    Solicitud.Notificacion.NO_CONFIGURADA: "advertencia",
}
