"""Admin de Django: solo soporte del superusuario técnico (ADM-12)."""

from django.contrib import admin
from django.db import transaction
from django.utils import timezone

from auditoria.services import Accion, registrar
from cuentas.models import EnlaceAcceso, Usuario

_EDITABLES = (("nombre", "nombre"), ("email", "correo"))


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    """Sin alta, sin borrado y sin contraseña: nadie la conoce ni la fija por otro (AUT-06).

    La empresa y los privilegios técnicos no se cambian aquí: mover a un cliente de empresa
    le daría los documentos de otra. Lo que sí se edita deja su evento de auditoría.
    """

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
    readonly_fields = (
        "uuid",
        "rut",
        "rol",
        "empresa",
        "is_staff",
        "is_superuser",
        "last_login",
        "creado_en",
        "actualizado_en",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        editados = [nombre for campo, nombre in _EDITABLES if campo in form.changed_data]
        cambio_de_estado = "is_active" in form.changed_data
        comunes = {"request": request, "actor": request.user, "empresa": obj.empresa, "objeto": obj}
        with transaction.atomic():
            super().save_model(request, obj, form, change)
            if editados:
                registrar(
                    Accion.USUARIO_EDITADO,
                    detalle="Desde el admin de Django: " + ", ".join(editados),
                    **comunes,
                )
            if cambio_de_estado and not obj.is_active:
                # Como en el panel: un enlace entregado antes no revive al reactivar.
                obj.enlaces.filter(usado_en__isnull=True, revocado_en__isnull=True).update(
                    revocado_en=timezone.now()
                )
                registrar(Accion.USUARIO_DESACTIVADO, detalle="Desde el admin de Django", **comunes)
            elif cambio_de_estado:
                registrar(Accion.USUARIO_REACTIVADO, detalle="Desde el admin de Django", **comunes)


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
