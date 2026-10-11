import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.models import ModeloConFechas
from documentos.almacenamiento import PATRON_CLAVE
from documentos.querysets import DocumentoQuerySet, SoloAgregar, VersionQuerySet
from documentos.validacion import FAMILIAS, VISIBLES_EN_NAVEGADOR


class Documento(ModeloConFechas):
    """Documento de una empresa, dentro de una de sus carpetas.

    El archivo vive en sus versiones: `version_vigente` es la que ve el cliente.
    `eliminado_en` marca la papelera (ADM-09).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "empresas.Empresa",
        verbose_name="empresa",
        on_delete=models.PROTECT,
        related_name="documentos",
    )
    # PROTECT: una carpeta con documentos, también los de la papelera, no se elimina (ADM-07).
    carpeta = models.ForeignKey(
        "empresas.Carpeta",
        verbose_name="carpeta",
        on_delete=models.PROTECT,
        related_name="documentos",
    )
    titulo = models.CharField("título", max_length=200)
    descripcion = models.CharField("descripción", max_length=500, blank=True)
    version_vigente = models.ForeignKey(
        "documentos.VersionDocumento",
        verbose_name="versión vigente",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    eliminado_en = models.DateTimeField("eliminado en", null=True, blank=True)
    eliminado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="eliminado por",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    objects = DocumentoQuerySet.as_manager()

    class Meta:
        verbose_name = "documento"
        verbose_name_plural = "documentos"
        ordering = ["titulo", "id"]
        indexes = [
            models.Index(
                fields=["carpeta", "eliminado_en", "titulo"], name="documento_carpeta_idx"
            ),
            models.Index(fields=["empresa", "eliminado_en"], name="documento_empresa_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(eliminado_en__isnull=True, eliminado_por__isnull=True)
                    | Q(eliminado_en__isnull=False)
                ),
                name="documento_eliminado_por_solo_en_papelera",
            ),
        ]

    def __str__(self):
        return self.titulo

    @property
    def en_papelera(self):
        return self.eliminado_en is not None


class VersionDocumento(models.Model):
    """Un archivo subido para un documento. Las versiones no se editan: solo se agregan.

    No hereda de ModeloConFechas: `subido_en` es su fecha de creación y la fila nunca cambia
    (mismo criterio que EventoAuditoria, DEC-70).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    documento = models.ForeignKey(
        Documento, verbose_name="documento", on_delete=models.PROTECT, related_name="versiones"
    )
    numero = models.PositiveIntegerField("número")
    # docs/<uuid_empresa>/<uuid_version>: sin nombre original ni RUT (DOC-03).
    clave = models.CharField("clave de almacenamiento", max_length=80, unique=True)
    nombre_original = models.CharField("nombre original saneado", max_length=150)
    tipo_mime = models.CharField("tipo MIME detectado", max_length=100)
    extension = models.CharField("extensión", max_length=10)
    tamano = models.PositiveBigIntegerField("tamaño en bytes")
    sha256 = models.CharField("SHA-256", max_length=64)
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="subido por",
        on_delete=models.PROTECT,
        related_name="+",
    )
    subido_en = models.DateTimeField("subido en", default=timezone.now, editable=False)

    objects = VersionQuerySet.as_manager()

    class Meta:
        verbose_name = "versión de documento"
        verbose_name_plural = "versiones de documentos"
        ordering = ["-numero"]
        indexes = [models.Index(fields=["-subido_en"], name="version_subido_en_idx")]
        constraints = [
            models.UniqueConstraint(
                fields=["documento", "numero"], name="version_numero_unico_por_documento"
            ),
            # La base rechaza cualquier clave con otra forma, aunque se salte el servicio.
            models.CheckConstraint(
                condition=Q(clave__regex=PATRON_CLAVE), name="version_clave_sin_datos"
            ),
            models.CheckConstraint(
                condition=Q(sha256__regex=r"^[0-9a-f]{64}$"), name="version_sha256_valido"
            ),
            models.CheckConstraint(condition=Q(tamano__gt=0), name="version_no_vacia"),
        ]

    def __str__(self):
        return f"{self.documento} (versión {self.numero})"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise SoloAgregar("Las versiones no se editan.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise SoloAgregar("Las versiones solo se borran al purgar la papelera.")

    @property
    def familia(self):
        """Tipo para el ícono: pdf, word, excel, powerpoint o imagen."""
        return FAMILIAS.get(self.extension, "")

    @property
    def se_puede_ver(self):
        """Si "Ver" lo abre en el navegador; el resto solo se descarga (DOC-05)."""
        return self.extension in VISIBLES_EN_NAVEGADOR
