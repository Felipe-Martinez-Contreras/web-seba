"""Formularios públicos de consulta y cotización (SOL-01 a SOL-07)."""

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.views.generic import FormView, TemplateView

from sitio.paginas import PaginaPublica
from solicitudes import antispam, services
from solicitudes.forms import FormularioConsulta, FormularioCotizacion

# Marca el mensaje de confirmación: la página de confirmación solo se muestra con él.
ETIQUETA_RECIBIDA = "solicitud-recibida"
AVISO_DESCARTE = "No pudimos procesar su solicitud. Inténtelo nuevamente en unos minutos."


class _Formulario(PaginaPublica, FormView):
    """Valida, pasa el antispam, guarda y redirige a la confirmación (SOL-05, SOL-06).

    Sin texto de política de privacidad los formularios no existen: la página muestra el
    contacto registrado y un envío hecho a mano responde 404 (SEG-12).
    """

    http_method_names = ["get", "post"]

    def post(self, request, *args, **kwargs):
        if not self.formularios:
            raise Http404
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        if antispam.revisar(self.request):
            # Mismo formulario, con lo escrito, y sin decir qué control actuó (SOL-04).
            return self.render_to_response(
                self.get_context_data(form=form, aviso=self._aviso_de_descarte())
            )
        services.recibir(form.tipo, form.cleaned_data)
        # El texto no menciona correos: lo que pase con la notificación no cambia lo que
        # ve el visitante (SOL-05, R4).
        messages.success(
            self.request,
            "Le responderemos al correo o teléfono indicado.",
            extra_tags=ETIQUETA_RECIBIDA,
        )
        return redirect("solicitudes:recibida")

    def form_invalid(self, form):
        return self.render_to_response(
            self.get_context_data(form=form, marca=antispam.marca_para_reintento(self.request))
        )

    def _aviso_de_descarte(self):
        medios = []
        if self.contacto.telefono:
            medios.append(f"al teléfono {self.contacto.telefono}")
        if self.contacto.email:
            medios.append(f"al correo {self.contacto.email}")
        if not medios:
            return AVISO_DESCARTE
        return f"{AVISO_DESCARTE} También puede contactarnos {' o '.join(medios)}."

    def get_context_data(self, **kwargs):
        kwargs.setdefault("marca", antispam.nueva_marca())
        contexto = super().get_context_data(**kwargs)
        contexto["formulario"] = contexto["form"]
        contexto["url_formulario"] = self.request.path
        return contexto


class Contacto(_Formulario):
    template_name = "solicitudes/contacto.html"
    form_class = FormularioConsulta
    nombre_de_pagina = "Contacto"


class Cotizacion(_Formulario):
    template_name = "solicitudes/cotizacion.html"
    form_class = FormularioCotizacion
    nombre_de_pagina = "Solicitar cotización"

    def get_initial(self):
        """Servicio preseleccionado desde su botón (PUB-03). El formulario ignora un
        identificador desconocido o de un servicio inactivo."""
        return {"servicio": self.request.GET.get("servicio", "")}


class Recibida(PaginaPublica, TemplateView):
    """Confirmación tras guardar (POST/redirect/GET). Solo se muestra a quien acaba de
    enviar: abrir la dirección sin haber enviado nada lleva al inicio, porque la página
    afirma que se recibió una solicitud (R4)."""

    template_name = "solicitudes/recibida.html"
    nombre_de_pagina = "Solicitud recibida"

    def get(self, request, *args, **kwargs):
        confirmaciones = [
            mensaje.message
            for mensaje in messages.get_messages(request)
            if ETIQUETA_RECIBIDA in mensaje.tags
        ]
        if not confirmaciones:
            return redirect("sitio:inicio")
        return self.render_to_response(self.get_context_data(detalle=confirmaciones[0]))
