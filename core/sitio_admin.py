from django.contrib.admin import AdminSite
from django.contrib.auth.views import redirect_to_login
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse


class SitioAdminTecnico(AdminSite):
    """Admin de Django para soporte: solo el superusuario técnico, con 2FA verificado (ADM-12).

    No tiene formulario de acceso propio: usa el de la aplicación, con su bloqueo y su
    segundo factor.
    """

    site_header = "Administración técnica"
    site_title = "Administración técnica"
    index_title = "Soporte"

    def has_permission(self, request):
        usuario = request.user
        verificar = getattr(usuario, "is_verified", None)
        return bool(usuario.is_active and usuario.is_staff and verificar and verificar())

    def login(self, request, extra_context=None):
        usuario = request.user
        if not usuario.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not usuario.is_staff:
            raise Http404
        if self.has_permission(request):
            return redirect("admin:index")
        return redirect_to_login(
            request.GET.get("next") or reverse("admin:index"),
            login_url=reverse("cuentas:verificacion"),
        )
