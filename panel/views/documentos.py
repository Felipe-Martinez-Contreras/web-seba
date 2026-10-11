"""Documentos de un cliente: subir, ver, descargar, editar, mover, reemplazar, eliminar y
restaurar (ADM-08, ADM-09, DOC-04)."""

from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.functional import cached_property
from django.views import View
from django.views.generic import FormView, TemplateView

from documentos import services, validacion
from documentos.forms import FormularioDocumento, FormularioMover
from documentos.models import Documento
from documentos.validacion import ArchivoRechazado
from panel.views.base import VistaDeCarpeta, VistaDeCliente, paginar

# La subida con JavaScript envía un archivo por petición y pide solo el resultado.
ENCABEZADO_FRAGMENTO = "fragmento"


class VistaDeDocumento(VistaDeCliente):
    """Vista sobre un documento de la empresa de la URL, fuera de la papelera. Un UUID de
    otra empresa, o de un documento eliminado, responde 404."""

    pestana = "documentos"
    en_papelera = False

    @cached_property
    def documento(self):
        documentos = Documento.objects.select_related("carpeta", "version_vigente")
        documentos = documentos.en_papelera() if self.en_papelera else documentos.vigentes()
        return get_object_or_404(documentos, pk=self.kwargs["documento"], empresa=self.empresa)

    def url_documento(self):
        return reverse("panel:documento", args=[self.empresa.pk, self.documento.pk])

    def url_carpeta(self):
        return reverse("panel:carpeta", args=[self.empresa.pk, self.documento.carpeta_id])

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["documento"] = self.documento
        contexto["migas"] = [
            *contexto["migas"],
            (self.documento.carpeta.nombre, self.url_carpeta()),
            (self.documento.titulo, self.url_documento()),
        ]
        return contexto


class CarpetaDetalle(VistaDeCarpeta, TemplateView):
    """Documentos de una carpeta, con la zona de subida."""

    template_name = "panel/carpeta.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        documentos = (
            self.carpeta.documentos.vigentes()
            .select_related("version_vigente")
            .order_by("titulo", "pk")
        )
        contexto.update(
            carpeta=self.carpeta,
            pagina=paginar(self.request, documentos),
            migas=[*contexto["migas"], (self.carpeta.nombre, "")],
            formatos=validacion.nombres_de_formatos(),
            extensiones=",".join("." + e for e in validacion.formatos_permitidos()),
            maximo_mb=settings.DOCUMENTOS_TAMANO_MAXIMO_MB,
            maximo_bytes=validacion.tamano_maximo(),
        )
        return contexto


class DocumentoSubir(CarpetaDetalle):
    """Recibe uno o varios archivos y responde el resultado de cada uno: aceptado, o
    rechazado con su motivo. Cada archivo se valida y se guarda por separado."""

    http_method_names = ["post"]

    def _subir(self, archivo):
        resultado = {"nombre": (archivo.name or "")[:150]}
        try:
            resultado["documento"] = services.subir(
                self.carpeta, archivo, actor=self.request.user, request=self.request
            )
        except ArchivoRechazado as rechazo:
            resultado["motivo"] = rechazo.motivo
        return resultado

    def post(self, request, **kwargs):
        resultados = [self._subir(archivo) for archivo in request.FILES.getlist("archivos")]
        if request.headers.get("X-Subida") == ENCABEZADO_FRAGMENTO:
            self.template_name = "panel/_resultados_subida.html"
            return self.render_to_response({"resultados": resultados, "empresa": self.empresa})
        if not resultados:
            messages.error(request, "Seleccione al menos un archivo para subir.")
            return redirect("panel:carpeta", self.empresa.pk, self.carpeta.pk)
        return self.render_to_response(self.get_context_data(resultados=resultados))


class DocumentoDetalle(VistaDeDocumento, TemplateView):
    """Ficha del documento: datos, historial de versiones y acciones."""

    template_name = "panel/documento.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(
            versiones=self.documento.versiones.select_related("subido_por"),
            formulario_mover=FormularioMover(documento=self.documento),
            formatos=validacion.nombres_de_formatos(),
            extensiones=",".join("." + e for e in validacion.formatos_permitidos()),
            maximo_mb=settings.DOCUMENTOS_TAMANO_MAXIMO_MB,
            maximo_bytes=validacion.tamano_maximo(),
            mensaje_eliminar=(
                "El cliente dejará de verlo de inmediato. Quedará en la papelera y podrá "
                f"restaurarlo durante {settings.PAPELERA_DIAS} días; después se borra de "
                "forma definitiva."
            ),
        )
        return contexto


class DocumentoEditar(VistaDeDocumento, FormView):
    template_name = "panel/documento_formulario.html"
    form_class = FormularioDocumento

    def get_initial(self):
        return {"titulo": self.documento.titulo, "descripcion": self.documento.descripcion}

    def form_valid(self, form):
        if form.has_changed():
            services.editar(
                self.documento,
                titulo=form.cleaned_data["titulo"],
                descripcion=form.cleaned_data["descripcion"],
                actor=self.request.user,
                request=self.request,
            )
            messages.success(self.request, "Se guardaron los cambios del documento.")
        return redirect(self.url_documento())

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["migas"] = [*contexto["migas"], ("Editar", "")]
        contexto["url_cancelar"] = self.url_documento()
        return contexto


class DocumentoMover(VistaDeDocumento, View):
    http_method_names = ["post"]

    def post(self, request, **kwargs):
        formulario = FormularioMover(request.POST, documento=self.documento)
        if not formulario.is_valid():
            messages.error(request, "Seleccione una carpeta de destino de este cliente.")
            return redirect(self.url_documento())
        carpeta = formulario.cleaned_data["carpeta"]
        services.mover(self.documento, carpeta, actor=request.user, request=request)
        messages.success(request, f"El documento se movió a la carpeta {carpeta.nombre}.")
        return redirect(self.url_documento())


class DocumentoReemplazar(VistaDeDocumento, View):
    """Sube un archivo nuevo, que pasa a ser la versión vigente (DOC-08). Con JavaScript,
    subida.js lo envía con barra de progreso y recibe solo el resultado."""

    http_method_names = ["post"]

    def _fragmento(self, archivo):
        resultado = {"nombre": (archivo.name or "")[:150]}
        try:
            version = services.reemplazar(
                self.documento, archivo, actor=self.request.user, request=self.request
            )
        except ArchivoRechazado as rechazo:
            resultado["motivo"] = rechazo.motivo
        else:
            resultado.update(version=version.numero, publicado_para=self.empresa.razon_social)
        return render(self.request, "componentes/resultado_subida.html", resultado)

    def post(self, request, **kwargs):
        archivo = request.FILES.get("archivo")
        if request.headers.get("X-Subida") == ENCABEZADO_FRAGMENTO:
            return self._fragmento(archivo) if archivo else HttpResponseBadRequest()
        if archivo is None:
            messages.error(request, "Seleccione el archivo que reemplazará al actual.")
            return redirect(self.url_documento())
        try:
            version = services.reemplazar(
                self.documento, archivo, actor=request.user, request=request
            )
        except ArchivoRechazado as rechazo:
            messages.error(request, f"El archivo no se aceptó. {rechazo.motivo}")
        else:
            messages.success(
                request,
                f"Se subió la versión {version.numero}. Es la que ahora ve el cliente.",
            )
        return redirect(self.url_documento())


class DocumentoEliminar(VistaDeDocumento, View):
    """Solo POST, tras el diálogo de confirmación. Envía a la papelera."""

    http_method_names = ["post"]

    def post(self, request, **kwargs):
        destino = self.url_carpeta()
        services.eliminar(self.documento, actor=request.user, request=request)
        messages.success(
            request,
            f"El documento {self.documento.titulo} se envió a la papelera. El cliente ya no lo ve.",
        )
        return redirect(destino)


class DocumentoRestaurar(VistaDeDocumento, View):
    http_method_names = ["post"]
    en_papelera = True

    def post(self, request, **kwargs):
        try:
            services.restaurar(self.documento, actor=request.user, request=request)
        except services.OperacionNoPermitida as error:
            messages.error(request, error.motivo)
            return redirect("panel:cliente_papelera", self.empresa.pk)
        messages.success(
            request,
            f"El documento {self.documento.titulo} se restauró en la carpeta "
            f"{self.documento.carpeta.nombre}. El cliente vuelve a verlo.",
        )
        return redirect(self.url_documento())


class _EntregaDeVersion(VistaDeDocumento, View):
    """Entrega una versión, vigente o anterior, de un documento que no está en la papelera."""

    http_method_names = ["get"]
    ver = False

    def get(self, request, **kwargs):
        version = get_object_or_404(self.documento.versiones, pk=kwargs["version"])
        try:
            return services.entregar(
                self.documento, version, ver=self.ver, actor=request.user, request=request
            )
        except services.ArchivoNoDisponible:
            raise Http404 from None


class VersionVer(_EntregaDeVersion):
    ver = True


class VersionDescargar(_EntregaDeVersion):
    pass


class ClientePapelera(VistaDeCliente, TemplateView):
    """Documentos eliminados del cliente, con los días que quedan para restaurarlos (ADM-09)."""

    template_name = "panel/papelera.html"
    pestana = "documentos"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        eliminados = (
            Documento.objects.en_papelera()
            .filter(empresa=self.empresa)
            .select_related("carpeta", "version_vigente", "eliminado_por")
            .order_by("-eliminado_en", "pk")
        )
        pagina = paginar(self.request, eliminados)
        pagina.object_list = list(pagina.object_list)
        limite = services.limite_de_papelera()
        for documento in pagina.object_list:
            documento.purga_prevista = services.purga_prevista(documento)
            documento.restaurable = documento.eliminado_en >= limite
        contexto.update(
            pagina=pagina,
            dias=settings.PAPELERA_DIAS,
            migas=[*contexto["migas"], ("Papelera", "")],
        )
        return contexto
