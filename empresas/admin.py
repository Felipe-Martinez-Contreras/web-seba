"""Admin de Django: solo soporte del superusuario técnico (ADM-12)."""

from django.contrib import admin

from empresas.models import Empresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "rut", "activa")
    list_filter = ("activa",)
    search_fields = ("rut", "razon_social", "nombre_fantasia")
    readonly_fields = ("creado_en", "actualizado_en")

    def has_delete_permission(self, request, obj=None):
        # Sin borrado definitivo de empresas (ADM-03).
        return False
