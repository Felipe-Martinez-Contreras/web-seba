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


class ImagenSitio(ModeloConFechas):
    """Imagen del sitio que el administrador cambió desde el panel (DEC-205). Sin fila, el
    sitio usa la original del repositorio; con fila y sin variantes, la original con el
    texto alternativo que se haya escrito."""

    class Ranura(models.TextChoices):
        PORTADA = "portada", "Foto de portada"
        CONTACTO = "contacto", "Foto del bloque de contacto"
        ACCESO = "acceso", "Foto de las pantallas de acceso"
        LOGO_FONDO_OSCURO = "logo-fondo-oscuro", "Logo sobre fondo azul marino"
        LOGO_FONDO_CLARO = "logo-fondo-claro", "Logo sobre fondo blanco"

    ranura = models.CharField("ranura", max_length=20, choices=Ranura, unique=True)
    alt = models.CharField("texto alternativo", max_length=200, blank=True)

    class Meta:
        verbose_name = "imagen del sitio"
        verbose_name_plural = "imágenes del sitio"

    def __str__(self):
        return self.get_ranura_display()


class VarianteImagen(models.Model):
    """Un tamaño de una imagen subida, ya re-codificado en el servidor: nunca el archivo
    original. Se entrega en /imagenes/<sha256>.<extensión>."""

    class Tipo(models.TextChoices):
        WEBP = "image/webp", "WebP"
        PNG = "image/png", "PNG"
        ICO = "image/x-icon", "ICO"

    imagen = models.ForeignKey(ImagenSitio, on_delete=models.CASCADE, related_name="variantes")
    nombre = models.CharField("variante", max_length=20)
    tipo_mime = models.CharField("tipo", max_length=20, choices=Tipo)
    sha256 = models.CharField("SHA-256", max_length=64, db_index=True)
    ancho = models.PositiveIntegerField("ancho")
    alto = models.PositiveIntegerField("alto")
    contenido = models.BinaryField("contenido")

    class Meta:
        verbose_name = "variante de imagen"
        verbose_name_plural = "variantes de imagen"
        constraints = [
            models.UniqueConstraint(fields=["imagen", "nombre"], name="variante_unica_por_imagen"),
        ]

    def __str__(self):
        return f"{self.imagen} ({self.nombre})"
