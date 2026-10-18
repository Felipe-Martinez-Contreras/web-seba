"""Contenido del sitio: datos del negocio, servicios e imágenes (ADM-10, DEC-205)."""

from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.views import View
from django.views.generic import FormView, TemplateView

from core.mixins import AdministradorMixin
from sitio import imagenes, pendientes, services
from sitio.forms import FormularioDatosNegocio, FormularioImagen, FormularioServicio
from sitio.models import DatosNegocio, Servicio

_GRUPOS = (
    ("Identidad y portada", ("nombre_comercial", "titular", "bajada", "presentacion")),
    ("Contacto", ("telefono", "email_publico", "whatsapp", "ubicacion", "horario")),
    ("Redes sociales", ("instagram", "linkedin", "facebook")),
    ("Política de privacidad", ("politica_privacidad",)),
)
_PESTANAS = (
    ("panel:contenido", "Datos del negocio"),
    ("panel:servicios", "Servicios"),
    ("panel:imagenes", "Imágenes del sitio"),
)


class _VistaDeContenido(AdministradorMixin):
    seccion = "contenido"
    ruta = ""

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["pestanas"] = [
            {"texto": texto, "url": reverse(ruta), "activa": ruta == self.ruta}
            for ruta, texto in _PESTANAS
        ]
        return contexto


class Contenido(_VistaDeContenido, FormView):
    """Datos del negocio. Cada dato pendiente lleva el marcador [COMPLETAR] (PUB-06)."""

    template_name = "panel/contenido.html"
    form_class = FormularioDatosNegocio
    ruta = "panel:contenido"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": DatosNegocio.cargar()}

    def form_valid(self, form):
        if form.has_changed():
            services.guardar_datos(form)
            messages.success(self.request, "Se guardaron los datos del negocio.")
        return redirect("panel:contenido")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        formulario = contexto["form"]
        datos = formulario.instance
        faltantes = {
            campo
            for campo in pendientes.CAMPOS_REQUERIDOS
            if pendientes.falta(getattr(datos, campo))
        }
        if not pendientes.politica_disponible(datos):
            faltantes.add("politica_privacidad")
        contexto.update(
            grupos=[
                (titulo, [(formulario[campo], campo in faltantes) for campo in campos])
                for titulo, campos in _GRUPOS
            ],
            marcador=pendientes.MARCADOR,
            politica_de_prueba=pendientes.de_prueba(datos.politica_privacidad),
        )
        return contexto


class Servicios(_VistaDeContenido, TemplateView):
    template_name = "panel/servicios.html"
    ruta = "panel:servicios"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["servicios"] = list(Servicio.objects.all())
        return contexto


class _VistaDeServicio(_VistaDeContenido):
    ruta = "panel:servicios"

    @cached_property
    def servicio(self):
        return get_object_or_404(Servicio, pk=self.kwargs["servicio"])


def _migas(titulo):
    return [("Servicios", reverse("panel:servicios")), (titulo, "")]


class ServicioNuevo(_VistaDeContenido, FormView):
    template_name = "panel/servicio_formulario.html"
    form_class = FormularioServicio
    ruta = "panel:servicios"

    def form_valid(self, form):
        servicio = services.crear_servicio(form)
        messages.success(self.request, f"Se creó el servicio {servicio.nombre}.")
        return redirect("panel:servicios")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["migas"] = _migas("Nuevo servicio")
        return contexto


class ServicioEditar(_VistaDeServicio, FormView):
    template_name = "panel/servicio_formulario.html"
    form_class = FormularioServicio

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": self.servicio}

    def form_valid(self, form):
        if form.has_changed():
            services.editar_servicio(form)
            messages.success(self.request, "Se guardaron los cambios del servicio.")
        return redirect("panel:servicios")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["edicion"] = True
        contexto["migas"] = _migas("Editar servicio")
        return contexto


class ServicioMover(_VistaDeServicio, View):
    http_method_names = ["post"]

    def post(self, request, **kwargs):
        direccion = request.POST.get("direccion")
        if direccion in (services.SUBIR, services.BAJAR):
            services.mover_servicio(self.servicio, direccion)
        return redirect("panel:servicios")


class ServicioEstado(_VistaDeServicio, View):
    """Activa o desactiva el servicio. No hay borrado: las solicitudes lo siguen nombrando."""

    http_method_names = ["post"]

    def post(self, request, **kwargs):
        activo = request.POST.get("activo") == "si"
        if services.cambiar_estado_servicio(self.servicio, activo):
            if activo:
                messages.success(request, f"{self.servicio.nombre} volvió a mostrarse en el sitio.")
            else:
                messages.success(request, f"{self.servicio.nombre} dejó de mostrarse en el sitio.")
        return redirect("panel:servicios")


class Imagenes(_VistaDeContenido, TemplateView):
    """Fotos de fondo y logo del sitio: vista previa, subir una nueva, texto alternativo y
    volver a la original (DEC-205)."""

    template_name = "panel/imagenes.html"
    ruta = "panel:imagenes"

    def formulario(self, ranura, actuales, datos=None, archivos=None):
        fila = actuales.fila(ranura)
        original = imagenes.ORIGINALES.get(ranura)
        alt_original = original.alt if original else ""
        return FormularioImagen(
            datos,
            archivos,
            ranura=ranura,
            alt_inicial=(fila.alt if fila else "") or alt_original,
            alt_original=alt_original,
            prefix=ranura,
        )

    def get_context_data(self, formulario_con_errores=None, **kwargs):
        contexto = super().get_context_data(**kwargs)
        actuales = imagenes.cargar()
        tarjetas = []
        for ranura in imagenes.Ranura:
            formulario = formulario_con_errores
            if formulario is None or formulario.ranura != ranura:
                formulario = self.formulario(ranura, actuales)
            fila = actuales.fila(ranura)
            tarjeta = {
                "ranura": ranura.value,
                "titulo": ranura.label,
                "formulario": formulario,
                "subida": actuales.subida(ranura),
                "modificada": fila is not None,
                "insignia": (
                    f"Subida el {timezone.localtime(fila.actualizado_en):%d-%m-%Y}"
                    if actuales.subida(ranura)
                    else ""
                ),
                "es_foto": imagenes.es_foto(ranura),
            }
            if imagenes.es_foto(ranura):
                tarjeta["foto"] = actuales.foto(ranura)
            elif ranura == imagenes.Ranura.LOGO_FONDO_OSCURO:
                tarjeta["simbolo"] = actuales.simbolo_sobre_oscuro
            else:
                tarjeta["simbolo"] = actuales.simbolo_sobre_claro
                tarjeta["simbolo_con_fondo"] = actuales.simbolo_con_fondo
            tarjetas.append(tarjeta)
        contexto.update(
            tarjetas=tarjetas,
            tamano_maximo_mb=imagenes.tamano_maximo() // (1024 * 1024),
        )
        return contexto


def _ranura(valor):
    try:
        return imagenes.Ranura(valor)
    except ValueError as error:
        raise Http404 from error


class ImagenCambiar(Imagenes):
    http_method_names = ["post"]

    def post(self, request, **kwargs):
        ranura = _ranura(kwargs["ranura"])
        formulario = self.formulario(ranura, imagenes.cargar(), request.POST, request.FILES)
        if formulario.is_valid():
            try:
                cambio = imagenes.cambiar(
                    ranura,
                    archivo=formulario.cleaned_data.get("archivo"),
                    alt=formulario.cleaned_data.get("alt", ""),
                    actor=request.user,
                    request=request,
                )
            except imagenes.ImagenRechazada as rechazo:
                formulario.add_error("archivo", rechazo.motivo)
            else:
                if cambio:
                    messages.success(request, f"Se guardó: {ranura.label.lower()}.")
                else:
                    messages.info(request, "No había cambios que guardar.")
                return redirect(reverse("panel:imagenes") + f"#imagen-{ranura.value}")
        return self.render_to_response(self.get_context_data(formulario_con_errores=formulario))


class ImagenRestaurar(_VistaDeContenido, View):
    http_method_names = ["post"]

    def post(self, request, **kwargs):
        ranura = _ranura(kwargs["ranura"])
        if imagenes.restaurar(ranura, actor=request.user, request=request):
            messages.success(request, f"Se volvió a la original: {ranura.label.lower()}.")
        return redirect(reverse("panel:imagenes") + f"#imagen-{ranura.value}")
