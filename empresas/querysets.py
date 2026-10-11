"""Consultas centralizadas de empresas y carpetas (sección 5, SEG-04)."""

from django.contrib.auth.hashers import UNUSABLE_PASSWORD_PREFIX
from django.db import models
from django.db.models import Count, Max, Q

from core import rut as utilidades_rut


class EmpresaQuerySet(models.QuerySet):
    def buscar(self, texto):
        """Filtra por razón social, nombre de fantasía o parte del RUT, con o sin puntos."""
        texto = (texto or "").strip()
        if not texto:
            return self
        condicion = Q(razon_social__icontains=texto) | Q(nombre_fantasia__icontains=texto)
        rut = utilidades_rut.normalizar(texto)
        if rut and rut.rstrip("K").isdigit():
            condicion |= Q(rut__contains=rut)
        return self.filter(condicion)

    def con_cuentas_pendientes(self):
        """Empresas activas con cuentas que aún no definen su contraseña, y cuántas son."""
        return (
            self.filter(activa=True)
            .annotate(
                cuentas_pendientes=Count(
                    "usuarios",
                    filter=Q(
                        usuarios__is_active=True,
                        usuarios__password__startswith=UNUSABLE_PASSWORD_PREFIX,
                    ),
                )
            )
            .filter(cuentas_pendientes__gt=0)
        )


class CarpetaQuerySet(models.QuerySet):
    def visibles_para(self, usuario):
        """Las carpetas que el usuario puede ver: todas para un administrador y, para un
        cliente, solo las de su empresa."""
        if usuario.es_administrador:
            return self
        if usuario.es_cliente and usuario.empresa_id:
            return self.filter(empresa_id=usuario.empresa_id)
        return self.none()

    def con_resumen(self):
        """Cada carpeta con su cantidad de documentos y la fecha del último subido o
        reemplazado. Los de la papelera no cuentan ni mueven la fecha."""
        vigente = Q(documentos__eliminado_en__isnull=True)
        return (
            self.annotate(
                cantidad=Count("documentos", filter=vigente),
                actualizado=Max("documentos__version_vigente__subido_en", filter=vigente),
            )
            # Explícito: al agrupar, Django deja de aplicar el orden por defecto del modelo.
            .order_by("orden", "nombre")
        )
