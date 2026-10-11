import datetime

from django.utils import timezone
from django.views.generic import TemplateView

from core.mixins import AdministradorMixin
from documentos.models import VersionDocumento
from empresas.models import Empresa

MAXIMO_EN_AVISO = 10
CLIENTES_RECIENTES = 5
DIAS_DE_DOCUMENTOS = 30


class Inicio(AdministradorMixin, TemplateView):
    """Inicio del panel (ADM-02), solo con datos que existen: los indicadores de solicitudes
    llegan con su modelo, en la Etapa 6."""

    template_name = "panel/inicio.html"
    seccion = "inicio"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        pendientes = list(
            Empresa.objects.con_cuentas_pendientes().order_by("razon_social")[: MAXIMO_EN_AVISO + 1]
        )
        contexto.update(
            clientes_activos=Empresa.objects.filter(activa=True).count(),
            # Archivos subidos o reemplazados en el período, sin contar los de la papelera.
            documentos_recientes=VersionDocumento.objects.filter(
                subido_en__gte=timezone.now() - datetime.timedelta(days=DIAS_DE_DOCUMENTOS),
                documento__eliminado_en__isnull=True,
            ).count(),
            clientes_recientes=Empresa.objects.order_by("-creado_en")[:CLIENTES_RECIENTES],
            con_cuentas_pendientes=pendientes[:MAXIMO_EN_AVISO],
            hay_mas_pendientes=len(pendientes) > MAXIMO_EN_AVISO,
        )
        return contexto
