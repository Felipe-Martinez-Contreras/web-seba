from django import forms
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm

from core.validators import validar_rut

AYUDA_CONTRASENA = (
    "Mínimo 12 caracteres. No use solo números ni una contraseña común o parecida a sus datos."
)


def _entrada_rut(**atributos):
    return forms.TextInput(
        attrs={
            "placeholder": "12.345.678-5",
            "autocomplete": "username",
            "autocapitalize": "characters",
            "spellcheck": "false",
            **atributos,
        }
    )


class FormularioAcceso(forms.Form):
    """Solo comprueba que los campos vengan: validar el RUT aquí daría una respuesta
    distinta de la genérica (AUT-02). Eso lo resuelve el servicio de acceso."""

    rut = forms.CharField(label="RUT", max_length=20, widget=_entrada_rut(autofocus=True))
    contrasena = forms.CharField(
        label="Contraseña",
        max_length=1024,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class FormularioRecuperacion(forms.Form):
    rut = forms.CharField(
        label="RUT",
        max_length=20,
        validators=[validar_rut],
        help_text="Con o sin puntos y guion.",
        widget=_entrada_rut(autofocus=True),
    )


class FormularioCodigo(forms.Form):
    codigo = forms.CharField(
        label="Código",
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "autofocus": True,
                "spellcheck": "false",
            }
        ),
    )


class FormularioVerificacion(FormularioCodigo):
    codigo = forms.CharField(
        label="Código",
        max_length=20,
        help_text="El código de 6 dígitos de su aplicación, o un código de recuperación.",
        widget=forms.TextInput(
            attrs={"autocomplete": "one-time-code", "autofocus": True, "spellcheck": "false"}
        ),
    )


class _TextosDeContrasena:
    """Etiquetas y ayudas propias en los formularios de contraseña de Django."""

    def _ajustar(self):
        self.fields["new_password1"].label = "Contraseña nueva"
        self.fields["new_password1"].help_text = AYUDA_CONTRASENA
        self.fields["new_password2"].label = "Repita la contraseña nueva"
        self.fields["new_password2"].help_text = ""


class FormularioDefinirContrasena(_TextosDeContrasena, SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ajustar()
        self.fields["new_password1"].widget.attrs["autofocus"] = True


class FormularioCambiarContrasena(_TextosDeContrasena, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ajustar()
        self.fields["old_password"].label = "Contraseña actual"
        self.fields["old_password"].widget.attrs.pop("autofocus", None)
