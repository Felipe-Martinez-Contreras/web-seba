"""Admin de Django: la auditoría se consulta, nunca se edita ni se borra (AUD-03)."""

from django.contrib import admin

from auditoria.models import EventoAuditoria


@admin.register(EventoAuditoria)
class EventoAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "accion", "actor", "rut_intentado", "empresa", "ip", "detalle")
    list_filter = ("accion",)
    search_fields = ("rut_intentado", "detalle")
    date_hierarchy = "fecha"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
