from django import forms

from auditoria.models import EventoAuditoria
from core import rut as utilidades_rut
from core.formularios import campo_de_fecha
from core.validators import validar_rut
from empresas.models import Empresa


class FormularioFiltros(forms.Form):
    """Filtros del listado de auditoría (ADM-11). Todos son opcionales."""

    empresa = forms.ModelChoiceField(
        label="Cliente",
        queryset=Empresa.objects.order_by("razon_social"),
        required=False,
        empty_label="Todos los clientes",
    )
    rut = forms.CharField(
        label="RUT del usuario",
        max_length=20,
        required=False,
        validators=[validar_rut],
        widget=forms.TextInput(attrs={"placeholder": "12.345.678-5", "spellcheck": "false"}),
    )
    accion = forms.ChoiceField(
        label="Acción",
        required=False,
        choices=[
            ("", "Todas las acciones"),
            *sorted(EventoAuditoria.Accion.choices, key=lambda opcion: opcion[1]),
        ],
    )
    desde = campo_de_fecha("Desde")
    hasta = campo_de_fecha("Hasta")

    def clean_rut(self):
        return utilidades_rut.normalizar(self.cleaned_data["rut"])

    def clean(self):
        datos = super().clean()
        if datos.get("desde") and datos.get("hasta") and datos["desde"] > datos["hasta"]:
            self.add_error("hasta", "La fecha final no puede ser anterior a la inicial.")
        return datos
