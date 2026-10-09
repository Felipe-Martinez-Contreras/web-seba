import uuid

from django.db import models

from core import rut as utilidades_rut
from core.fields import CampoRut
from core.models import ModeloConFechas


class Empresa(ModeloConFechas):
    """Empresa cliente, identificada por su RUT."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rut = CampoRut("RUT", unique=True)
    razon_social = models.CharField("razón social", max_length=200)
    nombre_fantasia = models.CharField("nombre de fantasía", max_length=200, blank=True)
    contacto_nombre = models.CharField("nombre del contacto", max_length=150, blank=True)
    contacto_email = models.EmailField("email del contacto", blank=True)
    contacto_telefono = models.CharField("teléfono del contacto", max_length=30, blank=True)
    activa = models.BooleanField("activa", default=True)
    # Solo para administradores: nunca se muestran al cliente.
    notas_internas = models.TextField("notas internas", blank=True)

    class Meta:
        verbose_name = "empresa"
        verbose_name_plural = "empresas"
        ordering = ["razon_social"]
        indexes = [models.Index(fields=["activa", "razon_social"], name="empresa_activa_razon_idx")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rut__regex=utilidades_rut.PATRON_NORMALIZADO),
                name="empresa_rut_normalizado",
            ),
        ]

    def __str__(self):
        return f"{self.razon_social} ({utilidades_rut.formatear(self.rut)})"
