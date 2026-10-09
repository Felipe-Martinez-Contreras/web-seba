from django.db import models


class ModeloConFechas(models.Model):
    """Base de todos los modelos: registra cuándo se creó y cuándo cambió por última vez."""

    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        abstract = True
