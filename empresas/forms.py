from django import forms

from core import rut as utilidades_rut
from core.validators import validar_rut
from empresas.models import Carpeta, Empresa


class FormularioEmpresa(forms.ModelForm):
    # El campo del modelo mide 9 caracteres (RUT normalizado); aquí se acepta con puntos y guion.
    rut = forms.CharField(
        label="RUT",
        max_length=20,
        validators=[validar_rut],
        help_text="RUT de la empresa, con o sin puntos y guion.",
        widget=forms.TextInput(attrs={"placeholder": "12.345.678-5", "spellcheck": "false"}),
    )

    class Meta:
        model = Empresa
        fields = [
            "rut",
            "razon_social",
            "nombre_fantasia",
            "contacto_nombre",
            "contacto_email",
            "contacto_telefono",
            "notas_internas",
        ]
        labels = {
            "razon_social": "Razón social",
            "nombre_fantasia": "Nombre de fantasía",
            "contacto_nombre": "Nombre del contacto",
            "contacto_email": "Correo del contacto",
            "contacto_telefono": "Teléfono del contacto",
            "notas_internas": "Notas internas",
        }
        help_texts = {
            "notas_internas": "Solo las ven los administradores; nunca se muestran al cliente.",
        }
        widgets = {"notas_internas": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["rut"] = utilidades_rut.formatear(self.instance.rut)

    def clean_rut(self):
        rut = utilidades_rut.normalizar(self.cleaned_data["rut"])
        repetida = Empresa.objects.filter(rut=rut)
        if self.instance.pk:
            repetida = repetida.exclude(pk=self.instance.pk)
        if repetida.exists():
            raise forms.ValidationError("Ya existe un cliente con ese RUT.")
        return rut


class FormularioEmpresaNueva(FormularioEmpresa):
    carpetas_base = forms.BooleanField(
        label="Crear las carpetas base",
        required=False,
        initial=True,
    )

    def __init__(self, *args, carpetas_base, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["carpetas_base"].help_text = ", ".join(carpetas_base) + "."


class FormularioCarpeta(forms.Form):
    """Nombre y descripción de una carpeta. Con `carpeta` edita esa; guardar es del servicio."""

    nombre = forms.CharField(
        label="Nombre", max_length=Carpeta._meta.get_field("nombre").max_length
    )
    descripcion = forms.CharField(
        label="Descripción",
        max_length=Carpeta._meta.get_field("descripcion").max_length,
        required=False,
    )

    def __init__(self, *args, empresa, carpeta=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        self.carpeta = carpeta
        if carpeta is not None:
            self.initial = {
                "nombre": carpeta.nombre,
                "descripcion": carpeta.descripcion,
                **self.initial,
            }

    def clean_nombre(self):
        nombre = " ".join(self.cleaned_data["nombre"].split())
        repetida = self.empresa.carpetas.filter(nombre__iexact=nombre)
        if self.carpeta is not None:
            repetida = repetida.exclude(pk=self.carpeta.pk)
        if repetida.exists():
            raise forms.ValidationError("Ya existe una carpeta con ese nombre en este cliente.")
        return nombre
