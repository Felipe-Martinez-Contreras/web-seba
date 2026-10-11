import datetime

from django.utils import timezone
from django.views.generic import TemplateView

from core.mixins import AdministradorMixin
from documentos.models import VersionDocumento
from empresas.models import Empresa
from sitio import services as contenido
from solicitudes.models import Solicitud

MAXIMO_EN_AVISO = 10
CLIENTES_RECIENTES = 5
DIAS_DE_DOCUMENTOS = 30
SOLICITUDES_RECIENTES = 5


class Inicio(AdministradorMixin, TemplateView):
    """Inicio del panel (ADM-02), con datos reales: indicadores, solicitudes y clientes
    recientes, y avisos de lo que requiere atención."""

    template_name = "panel/inicio.html"
    seccion = "inicio"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        pendientes = list(
            Empresa.objects.con_cuentas_pendientes().order_by("razon_social")[: MAXIMO_EN_AVISO + 1]
        )
        por_atender = Solicitud.objects.filter(estado=Solicitud.Estado.PENDIENTE)
        contexto.update(
            consultas_pendientes=por_atender.filter(tipo=Solicitud.Tipo.CONSULTA).count(),
            cotizaciones_pendientes=por_atender.filter(tipo=Solicitud.Tipo.COTIZACION).count(),
            solicitudes_recientes=Solicitud.objects.select_related("servicio")[
                :SOLICITUDES_RECIENTES
            ],
            notificaciones_fallidas=Solicitud.objects.con_notificacion_fallida().count(),
            contenido_pendiente=len(contenido.contenido_pendiente()),
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
