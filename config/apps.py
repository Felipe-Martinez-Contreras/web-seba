from django.contrib.admin.apps import AdminConfig


class AdminTecnicoConfig(AdminConfig):
    """Reemplaza el sitio de administración de Django por el que exige 2FA (ADM-12)."""

    default_site = "core.sitio_admin.SitioAdminTecnico"
