from django import forms

from documentos.models import Documento
from empresas.models import Carpeta


class FormularioDocumento(forms.Form):
    """Título y descripción de un documento. Guardar es del servicio."""

    titulo = forms.CharField(
        label="Título", max_length=Documento._meta.get_field("titulo").max_length
    )
    descripcion = forms.CharField(
        label="Descripción",
        max_length=Documento._meta.get_field("descripcion").max_length,
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="La ve el cliente en la ficha del documento.",
    )

    def clean_titulo(self):
        return " ".join(self.cleaned_data["titulo"].split())


class FormularioMover(forms.Form):
    """Carpeta de destino. Solo ofrece, y solo acepta, carpetas de la misma empresa (DOC-07)."""

    carpeta = forms.ModelChoiceField(
        label="Mover a la carpeta",
        queryset=Carpeta.objects.none(),
        empty_label="Seleccione una carpeta",
    )

    def __init__(self, *args, documento, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["carpeta"].queryset = Carpeta.objects.filter(
            empresa_id=documento.empresa_id
        ).exclude(pk=documento.carpeta_id)
