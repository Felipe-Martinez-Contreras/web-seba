from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from auditoria.services import Accion, registrar
from cuentas import services
from cuentas.models import EnlaceAcceso, Usuario


class Command(BaseCommand):
    help = (
        "Crea un administrador sin contraseña y muestra su enlace de activación (AUT-12). "
        "Con ese enlace define su contraseña y configura la verificación en dos pasos."
    )

    def add_arguments(self, parser):
        parser.add_argument("--rut", help="RUT de la persona, con o sin puntos y guion.")
        parser.add_argument("--nombre")
        parser.add_argument("--email")
        parser.add_argument(
            "--tecnico",
            action="store_true",
            help="Crea el superusuario técnico, que además puede entrar al admin de Django.",
        )

    def handle(self, *args, **opciones):
        datos = {}
        for campo, pregunta in (("rut", "RUT"), ("nombre", "Nombre"), ("email", "Email")):
            datos[campo] = (opciones[campo] or input(f"{pregunta}: ")).strip()

        crear = (
            Usuario.objects.create_superuser if opciones["tecnico"] else Usuario.objects.create_user
        )
        campos = {"nombre": datos["nombre"], "email": datos["email"]}
        if not opciones["tecnico"]:
            campos["rol"] = Usuario.Rol.ADMINISTRADOR
        try:
            usuario = crear(datos["rut"], **campos)
        except ValidationError as error:
            raise CommandError("; ".join(error.messages)) from None

        registrar(
            Accion.USUARIO_CREADO,
            objeto=usuario,
            detalle="Superusuario técnico" if opciones["tecnico"] else "Administrador",
        )
        _, token = services.generar_enlace(usuario, EnlaceAcceso.Tipo.ACTIVACION)
        self.stdout.write(self.style.SUCCESS(f"Administrador creado: {usuario}"))
        self.stdout.write(
            "Enlace de activación (un solo uso, no lo comparta por canales inseguros):"
        )
        self.stdout.write(services.url_del_enlace(EnlaceAcceso.Tipo.ACTIVACION, token))
