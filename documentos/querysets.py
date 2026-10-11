"""Consultas centralizadas de documentos y versiones (sección 5, SEG-04).

Toda vista llega a un documento por `visibles_para(usuario)` o, en el panel, dentro de la
empresa de la URL. Nunca con un `get(pk=…)` suelto.
"""

from django.db import models
from django.db.models import F


class SoloAgregar(Exception):
    """Las versiones de un documento no se editan: solo se agregan (sección 6)."""


class DocumentoQuerySet(models.QuerySet):
    def vigentes(self):
        return self.filter(eliminado_en__isnull=True)

    def en_papelera(self):
        return self.filter(eliminado_en__isnull=False)

    def visibles_para(self, usuario):
        """Lo que el usuario puede ver: todo para un administrador y, para un cliente, solo
        los documentos de su empresa que no están en la papelera."""
        if usuario.es_administrador:
            return self
        if usuario.es_cliente and usuario.empresa_id:
            return self.filter(empresa_id=usuario.empresa_id, eliminado_en__isnull=True)
        return self.none()

    def con_vigente(self):
        """Con la carpeta y la versión vigente ya cargadas: los listados no consultan por fila."""
        return self.select_related("carpeta", "version_vigente")

    def recientes(self):
        """Primero los últimos subidos o reemplazados."""
        return self.order_by("-version_vigente__subido_en", "pk")

    def buscar(self, texto):
        """Por título, sin distinguir mayúsculas ni tildes (CLI-03). Sin texto no hay resultados."""
        texto = (texto or "").strip()
        if not texto:
            return self.none()
        return self.filter(titulo__unaccent__icontains=texto)


class VersionQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise SoloAgregar("Las versiones no se editan.")

    def delete(self):
        raise SoloAgregar("Las versiones solo se borran al purgar la papelera.")

    def visibles_para(self, usuario):
        """Un cliente solo ve la versión vigente de los documentos que puede ver (DOC-08)."""
        if usuario.es_administrador:
            return self
        if usuario.es_cliente and usuario.empresa_id:
            return self.filter(
                documento__empresa_id=usuario.empresa_id,
                documento__eliminado_en__isnull=True,
                documento__version_vigente=F("pk"),
            )
        return self.none()

    def purgar(self):
        """Único borrado que existe: el de `services.purgar_vencidos` (ADM-09)."""
        return models.QuerySet.delete(self)[0]
