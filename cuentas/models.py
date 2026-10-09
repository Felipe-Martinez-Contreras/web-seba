import uuid

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from core import rut as utilidades_rut
from core.fields import CampoRut
from core.models import ModeloConFechas
from cuentas.managers import UsuarioManager


class Usuario(AbstractBaseUser, PermissionsMixin, ModeloConFechas):
    """Cuenta de una persona, identificada por su RUT de acceso.

    El rol de negocio vive en `rol`. `is_staff` e `is_superuser` quedan reservados al
    superusuario técnico y no otorgan ni representan el rol de administrador.
    El último acceso es `last_login`, heredado de AbstractBaseUser.
    """

    class Rol(models.TextChoices):
        ADMINISTRADOR = "administrador", "Administrador"
        CLIENTE = "cliente", "Cliente"

    # Identificador para las URL y la auditoría: el ID entero nunca sale de la aplicación.
    uuid = models.UUIDField(
        "identificador público", default=uuid.uuid4, unique=True, editable=False
    )
    rut = CampoRut("RUT de acceso", unique=True)
    nombre = models.CharField("nombre", max_length=150)
    email = models.EmailField("email", blank=True)
    rol = models.CharField("rol", max_length=20, choices=Rol.choices)
    empresa = models.ForeignKey(
        "empresas.Empresa",
        verbose_name="empresa",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="usuarios",
    )
    is_active = models.BooleanField("activo", default=True)
    is_staff = models.BooleanField("acceso al admin técnico", default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = "rut"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["nombre", "email"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["nombre"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(rol="cliente", empresa__isnull=False)
                    | Q(rol="administrador", empresa__isnull=True)
                ),
                name="usuario_rol_coherente_con_empresa",
                violation_error_message=(
                    "Un cliente debe pertenecer a una empresa y un administrador a ninguna."
                ),
            ),
            models.CheckConstraint(
                condition=~Q(rol="cliente") | Q(is_staff=False, is_superuser=False),
                name="usuario_cliente_sin_privilegios_tecnicos",
                violation_error_message="Un cliente no puede tener privilegios técnicos.",
            ),
            models.CheckConstraint(
                condition=Q(rut__regex=utilidades_rut.PATRON_NORMALIZADO),
                name="usuario_rut_normalizado",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({utilidades_rut.formatear(self.rut)})"

    def clean(self):
        super().clean()
        if self.rol == self.Rol.ADMINISTRADOR and not self.email:
            raise ValidationError({"email": "El email es obligatorio para los administradores."})

    @property
    def puede_acceder(self):
        """Cuenta activa y, si es de un cliente, con su empresa activa (AUT-11)."""
        return self.is_active and (self.empresa_id is None or self.empresa.activa)

    @property
    def es_administrador(self):
        return self.rol == self.Rol.ADMINISTRADOR

    @property
    def es_cliente(self):
        return self.rol == self.Rol.CLIENTE


class EnlaceAcceso(ModeloConFechas):
    """Enlace de un solo uso para definir la contraseña (AUT-06, AUT-07).

    Solo se guarda el SHA-256 del token: quien lea la base no puede reconstruir el enlace.
    """

    class Tipo(models.TextChoices):
        ACTIVACION = "activacion", "Activación"
        RESTABLECIMIENTO = "restablecimiento", "Restablecimiento"

    class Envio(models.TextChoices):
        # Vacío: el enlace se entrega por otro canal y no se envía por correo.
        PENDIENTE = "pendiente", "Pendiente"
        ENVIADA = "enviada", "Enviada"
        FALLIDA = "fallida", "Fallida"
        NO_CONFIGURADA = "no_configurada", "Correo no configurado"

    usuario = models.ForeignKey(
        Usuario, verbose_name="usuario", on_delete=models.CASCADE, related_name="enlaces"
    )
    tipo = models.CharField("tipo", max_length=20, choices=Tipo.choices)
    token_hash = models.CharField("hash del token", max_length=64, unique=True)
    expira_en = models.DateTimeField("expira en")
    usado_en = models.DateTimeField("usado en", null=True, blank=True)
    revocado_en = models.DateTimeField("revocado en", null=True, blank=True)
    creado_por = models.ForeignKey(
        Usuario,
        verbose_name="creado por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    envio = models.CharField("envío por correo", max_length=20, choices=Envio.choices, blank=True)
    envio_error = models.CharField("error de envío", max_length=200, blank=True)

    class Meta:
        verbose_name = "enlace de acceso"
        verbose_name_plural = "enlaces de acceso"
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["usuario", "usado_en", "revocado_en"], name="enlace_vigentes_idx")
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.usuario}"

    def esta_vigente(self, ahora):
        return (
            self.usado_en is None
            and self.revocado_en is None
            and self.expira_en > ahora
            and self.usuario.puede_acceder
        )
