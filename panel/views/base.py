"""Piezas comunes de las vistas del panel."""

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.functional import cached_property

from core.mixins import AdministradorMixin
from cuentas.models import Usuario
from empresas.models import Carpeta, Empresa

POR_PAGINA = 25

PESTANAS = (("documentos", "Documentos"), ("usuarios", "Usuarios"), ("actividad", "Actividad"))


def paginar(request, elementos):
    """Página pedida en `?page=`; un valor inválido o fuera de rango cae en la más cercana."""
    return Paginator(elementos, POR_PAGINA).get_page(request.GET.get("page"))


class VistaDeCliente(AdministradorMixin):
    """Vista que trabaja sobre la empresa de la URL. Todo lo demás (usuarios, carpetas) se
    busca siempre dentro de esa empresa: un UUID de otra responde 404."""

    seccion = "clientes"
    pestana = ""

    @cached_property
    def empresa(self):
        return get_object_or_404(Empresa, pk=self.kwargs["empresa"])

    def url_ficha(self, pestana="documentos"):
        return reverse(f"panel:cliente_{pestana}", args=[self.empresa.pk])

    def contexto_de_ficha(self):
        """Lo que necesita la cabecera de la ficha: empresa, pestañas y migas de pan."""
        return {
            "empresa": self.empresa,
            "pestanas": [
                {"texto": texto, "url": self.url_ficha(clave), "activa": clave == self.pestana}
                for clave, texto in PESTANAS
            ],
            "migas": [
                ("Clientes", reverse("panel:clientes")),
                (self.empresa.razon_social, self.url_ficha()),
            ],
        }

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(self.contexto_de_ficha())
        return contexto


class VistaDeUsuario(VistaDeCliente):
    pestana = "usuarios"

    @cached_property
    def cuenta(self):
        return get_object_or_404(
            Usuario.objects.select_related("empresa"),
            uuid=self.kwargs["usuario"],
            empresa=self.empresa,
            rol=Usuario.Rol.CLIENTE,
        )


class VistaDeCarpeta(VistaDeCliente):
    pestana = "documentos"

    @cached_property
    def carpeta(self):
        return get_object_or_404(Carpeta, pk=self.kwargs["carpeta"], empresa=self.empresa)
