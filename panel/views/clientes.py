"""Clientes (empresas): listado, alta, edición, estado y ficha (ADM-03 a ADM-05)."""

import copy

from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode
from django.views import View
from django.views.generic import FormView, TemplateView

from auditoria.models import EventoAuditoria
from core import correo
from core.mixins import AdministradorMixin
from core.paginacion import paginar
from cuentas.estados import anotar_estados
from documentos.models import Documento
from empresas import services
from empresas.forms import FormularioEmpresa, FormularioEmpresaNueva
from empresas.models import Empresa
from panel.views.base import VistaDeCliente

_ESTADOS = (("", "Todos", None), ("activos", "Activos", True), ("inactivos", "Inactivos", False))


class Clientes(AdministradorMixin, TemplateView):
    template_name = "panel/clientes.html"
    seccion = "clientes"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        busqueda = self.request.GET.get("q", "").strip()
        estado = self.request.GET.get("estado", "")
        clientes = Empresa.objects.buscar(busqueda).annotate(cantidad_usuarios=Count("usuarios"))
        for clave, _, activa in _ESTADOS:
            if clave and clave == estado:
                clientes = clientes.filter(activa=activa)

        def url(clave):
            filtros = {"q": busqueda, "estado": clave}
            consulta = urlencode({nombre: valor for nombre, valor in filtros.items() if valor})
            return reverse("panel:clientes") + (f"?{consulta}" if consulta else "")

        contexto.update(
            pagina=paginar(self.request, clientes.order_by("razon_social")),
            busqueda=busqueda,
            buscador_valor=busqueda,
            url_sin_busqueda=reverse("panel:clientes"),
            pestanas=[
                {"texto": texto, "url": url(clave), "activa": clave == estado}
                for clave, texto, _ in _ESTADOS
            ],
        )
        return contexto


class ClienteNuevo(AdministradorMixin, FormView):
    template_name = "panel/cliente_formulario.html"
    form_class = FormularioEmpresaNueva
    seccion = "clientes"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "carpetas_base": settings.CARPETAS_BASE}

    def form_valid(self, form):
        empresa = services.crear_empresa(
            form,
            con_carpetas_base=form.cleaned_data["carpetas_base"],
            actor=self.request.user,
            request=self.request,
        )
        messages.success(
            self.request, f"Se creó el cliente {empresa.razon_social}. Ahora cree sus usuarios."
        )
        return redirect("panel:cliente_usuarios", empresa.pk)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["migas"] = [("Clientes", reverse("panel:clientes")), ("Nuevo cliente", "")]
        contexto["url_cancelar"] = reverse("panel:clientes")
        return contexto


class ClienteEditar(VistaDeCliente, FormView):
    template_name = "panel/cliente_formulario.html"
    form_class = FormularioEmpresa

    def get_form_kwargs(self):
        # Una copia: validar un formulario con errores no debe alterar la empresa que
        # muestra la página.
        return {**super().get_form_kwargs(), "instance": copy.copy(self.empresa)}

    def form_valid(self, form):
        if form.has_changed():
            services.editar_empresa(form, actor=self.request.user, request=self.request)
            messages.success(self.request, "Se guardaron los cambios del cliente.")
        return redirect(self.url_ficha())

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["migas"] = [*contexto["migas"], ("Editar", "")]
        contexto["url_cancelar"] = self.url_ficha()
        contexto["edicion"] = True
        return contexto


class ClienteEstado(VistaDeCliente, View):
    """Desactiva o reactiva la empresa (ADM-03). Solo POST, tras el diálogo de confirmación."""

    http_method_names = ["post"]

    def post(self, request, **kwargs):
        activa = request.POST.get("activa") == "si"
        if services.cambiar_estado_empresa(
            self.empresa, activa, actor=request.user, request=request
        ):
            if activa:
                messages.success(request, "El cliente quedó activo: sus usuarios pueden ingresar.")
            else:
                messages.success(
                    request,
                    "El cliente quedó inactivo: sus usuarios ya no pueden ingresar al portal.",
                )
        return redirect(self.url_ficha())


class Cliente(VistaDeCliente, View):
    """Entrada de la ficha: lleva a su primera pestaña."""

    http_method_names = ["get"]

    def get(self, request, **kwargs):
        return redirect(self.url_ficha())


class ClienteDocumentos(VistaDeCliente, TemplateView):
    """Pestaña Documentos: las carpetas del cliente, con cuántos documentos tiene cada una,
    y el acceso a la papelera (ADM-07, ADM-08, ADM-09)."""

    template_name = "panel/cliente_documentos.html"
    pestana = "documentos"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        eliminado = Q(documentos__eliminado_en__isnull=False)
        contexto["carpetas"] = list(
            self.empresa.carpetas.con_resumen().annotate(
                en_papelera=Count("documentos", filter=eliminado)
            )
        )
        en_papelera = Documento.objects.en_papelera().filter(empresa=self.empresa).count()
        contexto["en_papelera"] = en_papelera
        contexto["en_papelera_texto"] = str(en_papelera)
        return contexto


class ClienteUsuarios(VistaDeCliente, TemplateView):
    template_name = "panel/cliente_usuarios.html"
    pestana = "usuarios"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        pagina = paginar(self.request, self.empresa.usuarios.order_by("nombre", "pk"))
        pagina.object_list = anotar_estados(pagina.object_list)
        contexto["pagina"] = pagina
        contexto["correo_configurado"] = correo.correo_configurado()
        return contexto


class ClienteActividad(VistaDeCliente, TemplateView):
    """Auditoría filtrada por la empresa (ADM-05)."""

    template_name = "panel/cliente_actividad.html"
    pestana = "actividad"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        eventos = EventoAuditoria.objects.filter(empresa=self.empresa).select_related(
            "actor", "empresa"
        )
        contexto["pagina"] = paginar(self.request, eventos)
        contexto["url_auditoria"] = (
            reverse("panel:auditoria") + "?" + urlencode({"empresa": self.empresa.pk})
        )
        return contexto
