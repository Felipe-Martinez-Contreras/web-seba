"""Admin de Django: solo soporte del superusuario técnico (ADM-12)."""

from django.contrib import admin

from cuentas.models import EnlaceAcceso, Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    """Sin alta, sin borrado y sin contraseña: nadie la conoce ni la fija por otro (AUT-06)."""

    list_display = ("rut", "nombre", "rol", "empresa", "is_active", "last_login")
    list_filter = ("rol", "is_active")
    search_fields = ("rut", "nombre", "email")
    fields = (
        "uuid",
        "rut",
        "nombre",
        "email",
        "rol",
        "empresa",
        "is_active",
        "is_staff",
        "is_superuser",
        "last_login",
        "creado_en",
        "actualizado_en",
    )
    readonly_fields = ("uuid", "rut", "rol", "last_login", "creado_en", "actualizado_en")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EnlaceAcceso)
class EnlaceAccesoAdmin(admin.ModelAdmin):
    """Solo lectura. El hash del token no se muestra."""

    list_display = ("usuario", "tipo", "creado_en", "expira_en", "usado_en", "revocado_en", "envio")
    list_filter = ("tipo", "envio")
    fields = (
        "usuario",
        "tipo",
        "creado_por",
        "creado_en",
        "expira_en",
        "usado_en",
        "revocado_en",
        "envio",
        "envio_error",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
