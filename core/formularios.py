"""Campos de formulario que comparten varias pantallas."""

from django import forms


def campo_de_fecha(etiqueta):
    # El control nativo de fecha siempre envía y espera aaaa-mm-dd, sea cual sea el idioma.
    return forms.DateField(
        label=etiqueta,
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
