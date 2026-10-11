from django.db import models
from django.db.models.functions import Lower

from core.models import ModeloConFechas

# Íconos que puede llevar un servicio: lista fija del set de Lucide (sección 6). La clave es
# el nombre del archivo en templates/iconos.
ICONOS = [
    ("shield-check", "Escudo"),
    ("triangle-alert", "Advertencia"),
    ("hard-hat", "Casco"),
    ("clipboard-check", "Lista de verificación"),
    ("file-check", "Documento aprobado"),
    ("graduation-cap", "Capacitación"),
    ("building-2", "Edificio"),
    ("search-check", "Inspección"),
    ("flame", "Fuego"),
    ("heart-pulse", "Salud"),
    ("scale", "Normativa"),
    ("users", "Personas"),
]

ID_UNICO = 1


class ServicioQuerySet(models.QuerySet):
    def activos(self):
        return self.filter(activo=True)


class Servicio(ModeloConFechas):
    """Servicio que se ofrece en el sitio público. Se edita desde el panel (ADM-10) y no se
    borra: se desactiva, porque las solicitudes recibidas lo siguen nombrando."""

    nombre = models.CharField("nombre", max_length=120)
    slug = models.SlugField("identificador en la dirección", max_length=140, unique=True)
    icono = models.CharField("ícono", max_length=30, choices=ICONOS, default="shield-check")
    resumen = models.CharField("resumen", max_length=200, blank=True)
    descripcion = models.TextField("descripción", blank=True)
    orden = models.PositiveIntegerField("orden", default=0)
    activo = models.BooleanField("activo", default=True)

    objects = ServicioQuerySet.as_manager()

    class Meta:
        verbose_name = "servicio"
        verbose_name_plural = "servicios"
        ordering = ["orden", "nombre"]
        indexes = [models.Index(fields=["activo", "orden"], name="servicio_activo_orden_idx")]
        constraints = [
            models.UniqueConstraint(
                Lower("nombre"),
                name="servicio_nombre_unico",
                violation_error_message="Ya existe un servicio con ese nombre.",
            ),
        ]

    def __str__(self):
        return self.nombre


class DatosNegocio(ModeloConFechas):
    """Datos del negocio que muestra el sitio. Registro único, editable desde el panel.

    Todo puede estar vacío: lo que falta no se muestra (PUB-05) y queda listado como
    pendiente (sitio/pendientes.py).
    """

    id = models.PositiveSmallIntegerField(primary_key=True, default=ID_UNICO, editable=False)
    nombre_comercial = models.CharField("nombre comercial", max_length=150, blank=True)
    titular = models.CharField("titular de la portada", max_length=150, blank=True)
    bajada = models.CharField("bajada de la portada", max_length=300, blank=True)
    presentacion = models.TextField("presentación", blank=True)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    email_publico = models.EmailField("correo público", blank=True)
    whatsapp = models.CharField("WhatsApp", max_length=30, blank=True)
    ubicacion = models.CharField("comuna o región", max_length=100, blank=True)
    horario = models.CharField("horario de atención", max_length=150, blank=True)
    instagram = models.URLField("Instagram", blank=True)
    linkedin = models.URLField("LinkedIn", blank=True)
    facebook = models.URLField("Facebook", blank=True)
    politica_privacidad = models.TextField("texto de la política de privacidad", blank=True)

    class Meta:
        verbose_name = "datos del negocio"
        verbose_name_plural = "datos del negocio"
        constraints = [
            models.CheckConstraint(condition=models.Q(id=ID_UNICO), name="datos_negocio_unico"),
        ]

    def __str__(self):
        return self.nombre_comercial or "Datos del negocio"

    @classmethod
    def cargar(cls):
        """El registro único. Lo crea la migración inicial; si faltara, se crea vacío."""
        return cls.objects.get_or_create(pk=ID_UNICO)[0]
