from django.core.management.base import BaseCommand, CommandError

from auditoria.services import Accion, registrar
from core import rut as utilidades_rut
from cuentas import dos_factores, services
from cuentas.models import EnlaceAcceso, Usuario


class Command(BaseCommand):
    help = (
        "Elimina el 2FA de un administrador y genera el enlace con el que podrá volver a "
        "configurarlo (AUT-10). Requiere acceso al servidor."
    )

    def add_arguments(self, parser):
        parser.add_argument("rut", help="RUT del administrador, con o sin puntos y guion.")

    def handle(self, *args, **opciones):
        if not utilidades_rut.es_valido(opciones["rut"]):
            raise CommandError("El RUT no es válido.")
        usuario = Usuario.objects.filter(rut=opciones["rut"], rol=Usuario.Rol.ADMINISTRADOR).first()
        if usuario is None:
            raise CommandError("No existe un administrador con ese RUT.")
        if not usuario.is_active:
            raise CommandError("La cuenta está desactivada: actívela antes de restablecer su 2FA.")

        eliminados = dos_factores.restablecer(usuario)
        registrar(Accion.DOS_FACTORES_RESTABLECIDO, objeto=usuario, detalle="Por comando")
        # El 2FA solo se enrola en la sesión que usa un enlace: sin él no podría volver a entrar.
        _, token = services.generar_enlace(usuario, EnlaceAcceso.Tipo.RESTABLECIMIENTO)
        self.stdout.write(
            self.style.SUCCESS(f"2FA restablecido para {usuario} ({eliminados} registros).")
        )
        self.stdout.write(
            "Enlace para definir una contraseña nueva y configurar el 2FA "
            "(un solo uso, vence pronto):"
        )
        self.stdout.write(services.url_del_enlace(EnlaceAcceso.Tipo.RESTABLECIMIENTO, token))
