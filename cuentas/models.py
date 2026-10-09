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
    def es_administrador(self):
        return self.rol == self.Rol.ADMINISTRADOR

    @property
    def es_cliente(self):
        return self.rol == self.Rol.CLIENTE
