"""Formularios públicos de consulta y cotización (SOL-01 a SOL-03) y filtros de la bandeja."""

import re

from django import forms
from django.core.exceptions import ValidationError

from core.formularios import campo_de_fecha
from sitio.models import Servicio
from solicitudes.models import OTRO_SERVICIO, Solicitud

MENSAJE_MAXIMO = 2000
OTRO = "otro"
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_TELEFONO = re.compile(r"[\d\s()+.-]+")


def validar_una_linea(valor):
    """Estos datos van al asunto y a los encabezados del correo de notificación: sin saltos
    de línea ni otros caracteres de control."""
    if _CONTROL.search(valor):
        raise ValidationError("Este dato no admite saltos de línea ni caracteres especiales.")


def validar_telefono(valor):
    if not _TELEFONO.fullmatch(valor) or sum(c.isdigit() for c in valor) < 8:
        raise ValidationError("Ingrese un teléfono válido, por ejemplo +56 9 1234 5678.")


def _texto(etiqueta, largo, *, obligatorio=True, **atributos):
    return forms.CharField(
        label=etiqueta,
        max_length=largo,
        required=obligatorio,
        validators=[validar_una_linea],
        widget=forms.TextInput(attrs=atributos),
    )


class FormularioConsulta(forms.Form):
    """Consulta (SOL-01). Los datos válidos se entregan al servicio, que guarda."""

    tipo = Solicitud.Tipo.CONSULTA

    nombre = _texto("Nombre completo", 150, autocomplete="name")
    email = forms.EmailField(
        label="Correo electrónico",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    telefono = forms.CharField(
        label="Teléfono",
        max_length=30,
        required=False,
        validators=[validar_telefono],
        widget=forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}),
    )
    mensaje = forms.CharField(
        label="Mensaje",
        max_length=MENSAJE_MAXIMO,
        help_text=f"Máximo {MENSAJE_MAXIMO:,} caracteres.".replace(",", "."),
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    consentimiento = forms.BooleanField(
        label="Acepto la política de privacidad",
        error_messages={
            "required": "Debe aceptar la política de privacidad para enviar el formulario."
        },
    )


class FormularioCotizacion(FormularioConsulta):
    """Solicitud de cotización (SOL-02). No calcula ni muestra precios (R6)."""

    tipo = Solicitud.Tipo.COTIZACION
    field_order = [
        "nombre",
        "email",
        "telefono",
        "empresa",
        "servicio",
        "trabajadores",
        "comuna",
        "mensaje",
        "consentimiento",
    ]

    empresa = _texto("Empresa", 200, obligatorio=False, autocomplete="organization")
    servicio = forms.ChoiceField(label="Servicio de interés")
    trabajadores = forms.ChoiceField(
        label="Cantidad de trabajadores",
        required=False,
        choices=[("", "Seleccione una opción"), *Solicitud.Trabajadores.choices],
    )
    comuna = _texto("Comuna o región", 100, obligatorio=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["telefono"].required = True
        self.servicios = {servicio.slug: servicio for servicio in Servicio.objects.activos()}
        self.fields["servicio"].choices = [
            ("", "Seleccione una opción"),
            *((slug, servicio.nombre) for slug, servicio in self.servicios.items()),
            (OTRO, OTRO_SERVICIO),
        ]

    def clean_servicio(self):
        """Devuelve el servicio elegido, o None para "Otro / no estoy seguro"."""
        return self.servicios.get(self.cleaned_data["servicio"])


class FormularioFiltros(forms.Form):
    """Filtros de la bandeja de solicitudes (SOL-09). Todos son opcionales."""

    q = forms.CharField(
        label="Buscar",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Nombre, correo o empresa"}),
    )
    estado = forms.ChoiceField(
        label="Estado",
        required=False,
        choices=[("", "Todos los estados"), *Solicitud.Estado.choices],
    )
    desde = campo_de_fecha("Desde")
    hasta = campo_de_fecha("Hasta")

    def clean(self):
        datos = super().clean()
        if datos.get("desde") and datos.get("hasta") and datos["desde"] > datos["hasta"]:
            self.add_error("hasta", "La fecha final no puede ser anterior a la inicial.")
        return datos


class FormularioEstado(forms.Form):
    estado = forms.ChoiceField(label="Estado", choices=Solicitud.Estado.choices)


class FormularioNotas(forms.Form):
    notas_internas = forms.CharField(
        label="Notas internas",
        required=False,
        max_length=5000,
        help_text="Solo las ven los administradores.",
        widget=forms.Textarea(attrs={"rows": 5}),
    )
