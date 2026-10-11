from django import forms
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm

from core import rut as utilidades_rut
from core.validators import validar_rut
from cuentas.models import Usuario

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


class FormularioCliente(forms.Form):
    """Datos de la cuenta de un cliente, para el panel (ADM-06).

    Con `usuario` edita esa cuenta; su RUT solo se puede cambiar mientras está pendiente.
    """

    rut = forms.CharField(
        label="RUT",
        max_length=20,
        validators=[validar_rut],
        help_text="RUT de la persona, con o sin puntos y guion. Con él ingresará al portal.",
        widget=_entrada_rut(autocomplete="off"),
    )
    nombre = forms.CharField(label="Nombre", max_length=150)
    email = forms.EmailField(
        label="Correo",
        max_length=254,
        required=False,
        help_text="A este correo llegan los enlaces para definir o recuperar la contraseña.",
    )

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        if usuario is not None:
            self.initial = {
                "rut": utilidades_rut.formatear(usuario.rut),
                "nombre": usuario.nombre,
                "email": usuario.email,
                **self.initial,
            }
            if usuario.has_usable_password():
                self.fields["rut"].disabled = True
                self.fields[
                    "rut"
                ].help_text = "El RUT no se puede cambiar una vez que la cuenta fue activada."

    def clean_rut(self):
        rut = utilidades_rut.normalizar(self.cleaned_data["rut"])
        repetido = Usuario.objects.filter(rut=rut)
        if self.usuario is not None:
            repetido = repetido.exclude(pk=self.usuario.pk)
        if repetido.exists():
            raise forms.ValidationError("Ya existe una cuenta con ese RUT.")
        return rut


class FormularioClienteNuevo(FormularioCliente):
    por_correo = forms.BooleanField(
        label="Enviar también el enlace por correo",
        required=False,
        help_text="Solo se envía si la cuenta tiene un correo. El enlace igual se mostrará "
        "para copiarlo.",
    )

    def __init__(self, *args, correo_configurado, **kwargs):
        super().__init__(*args, **kwargs)
        if not correo_configurado:
            # Sin servidor de correo no se ofrece lo que no se puede cumplir (R4).
            del self.fields["por_correo"]


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
