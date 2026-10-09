"""Página de referencia de componentes. Solo se publica en desarrollo (config/urls.py)."""

from django import forms
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.decorators.http import require_GET

from core.validators import validar_rut


class FormularioDeReferencia(forms.Form):
    """Formulario de muestra para ver los campos con ayuda y con error."""

    rut = forms.CharField(
        label="RUT",
        help_text="Con o sin puntos y guion.",
        validators=[validar_rut],
    )
    telefono = forms.CharField(label="Teléfono", required=False)
    mensaje = forms.CharField(label="Mensaje", widget=forms.Textarea(attrs={"rows": 3}))


@require_GET
def componentes(request):
    messages.success(request, "Así se ve la confirmación después de una acción.")
    contexto = {
        "formulario": FormularioDeReferencia(),
        "formulario_con_errores": FormularioDeReferencia({"rut": "12.345.678-9", "mensaje": ""}),
        "pagina": Paginator(range(1, 76), 25).page(2),
        "migas": [("Nivel 1", "#"), ("Nivel 2", "#"), ("Página actual", "")],
        "menu_panel": [
            {"texto": "Elemento activo", "url": "#", "activo": True},
            {"texto": "Otro elemento", "url": "#", "activo": False},
        ],
        "enlaces_publicos": [("Enlace", "#"), ("Otro enlace", "#")],
        "contacto_lineas": ["Línea de contacto de muestra"],
        "enlaces_pie": [("Enlace del pie", "#")],
    }
    return render(request, "core/referencia/componentes.html", contexto)


@require_GET
def error_404(request):
    return render(request, "404.html", status=404)


@require_GET
def error_500(request):
    return render(request, "500.html", status=500)
