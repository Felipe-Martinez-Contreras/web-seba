from django import forms
from django.conf import settings

from sitio.models import DatosNegocio, Servicio


class FormularioDatosNegocio(forms.ModelForm):
    """Datos del negocio (ADM-10). Todo es opcional: lo que falta no se publica."""

    class Meta:
        model = DatosNegocio
        fields = [
            "nombre_comercial",
            "titular",
            "bajada",
            "presentacion",
            "telefono",
            "email_publico",
            "whatsapp",
            "ubicacion",
            "horario",
            "instagram",
            "linkedin",
            "facebook",
            "politica_privacidad",
        ]
        labels = {
            "nombre_comercial": "Nombre comercial",
            "titular": "Titular de la portada",
            "bajada": "Bajada de la portada",
            "presentacion": "Presentación",
            "telefono": "Teléfono",
            "email_publico": "Correo público",
            "ubicacion": "Comuna o región",
            "horario": "Horario de atención",
            "politica_privacidad": "Texto de la política de privacidad",
        }
        help_texts = {
            "titular": "Frase principal del inicio. Sin titular, la portada no se muestra.",
            "bajada": "Una o dos líneas bajo el titular.",
            "presentacion": "Se muestra en la página Servicios. Texto simple, sin formato.",
            "whatsapp": "Número con código de país, por ejemplo +56 9 1234 5678.",
            "instagram": "Dirección completa del perfil. Si queda vacío, no se muestra.",
            "linkedin": "Dirección completa del perfil. Si queda vacío, no se muestra.",
            "facebook": "Dirección completa de la página. Si queda vacío, no se muestra.",
            "politica_privacidad": (
                "Texto que entrega el responsable del negocio. Sin este texto, los "
                "formularios del sitio no se muestran."
            ),
        }
        widgets = {
            "bajada": forms.Textarea(attrs={"rows": 2}),
            "presentacion": forms.Textarea(attrs={"rows": 5}),
            "politica_privacidad": forms.Textarea(attrs={"rows": 12}),
        }

    def clean(self):
        datos = super().clean()
        # Los enlaces a redes se publican como href: solo direcciones web.
        for red in ("instagram", "linkedin", "facebook"):
            url = datos.get(red)
            if url and not url.startswith("https://"):
                self.add_error(red, "La dirección debe empezar con https://.")
        return datos


class FormularioServicio(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ["nombre", "icono", "resumen", "descripcion"]
        labels = {"icono": "Ícono", "descripcion": "Descripción"}
        help_texts = {
            "resumen": "Una línea para la tarjeta del inicio.",
            "descripcion": "Se muestra en la página Servicios. Texto simple, sin formato.",
        }
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 5})}

    def clean_nombre(self):
        nombre = " ".join(self.cleaned_data["nombre"].split())
        repetido = Servicio.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            repetido = repetido.exclude(pk=self.instance.pk)
        if repetido.exists():
            raise forms.ValidationError("Ya existe un servicio con ese nombre.")
        return nombre


class FormularioImagen(forms.Form):
    """Imagen nueva y texto alternativo de una ranura (DEC-205). El formato y el tamaño los
    comprueba `sitio.procesar_imagen` sobre el contenido: el `accept` del campo solo ayuda a
    elegir el archivo."""

    archivo = forms.FileField(label="Imagen nueva", required=False)
    alt = forms.CharField(label="Texto alternativo", max_length=200, required=False)

    def __init__(self, *args, ranura, alt_inicial, alt_original, **kwargs):
        super().__init__(*args, initial={"alt": alt_inicial}, **kwargs)
        self.ranura = ranura
        self.alt_original = alt_original
        self.es_foto = bool(alt_original)
        archivo = self.fields["archivo"]
        if self.es_foto:
            archivo.widget.attrs["accept"] = "image/jpeg,image/png,image/webp"
            archivo.help_text = (
                f"JPG, PNG o WebP, de hasta {settings.IMAGENES_TAMANO_MAXIMO_MB} MB. Mejor "
                "horizontal y de al menos 1.920 px de ancho. El sitio la reduce y le quita los "
                "datos de la cámara."
            )
            self.fields["alt"].required = True
            self.fields["alt"].help_text = (
                "Describa lo que se ve, para quien no puede ver la imagen. Por ejemplo: "
                "«Casco de seguridad sobre una mesa de obra»."
            )
        else:
            archivo.required = True
            archivo.widget.attrs["accept"] = "image/png"
            archivo.help_text = (
                "PNG cuadrado, de 180 a 2.048 px por lado (se recomienda 512 px), con fondo "
                "transparente."
            )
            del self.fields["alt"]

    def clean(self):
        datos = super().clean()
        if (
            self.es_foto
            and datos.get("archivo")
            and " ".join(datos.get("alt", "").split()) == self.alt_original
        ):
            self.add_error(
                "alt",
                "El texto describe la foto original. Escriba uno que describa la foto nueva.",
            )
        return datos
