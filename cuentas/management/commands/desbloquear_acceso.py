import ipaddress

from django.core.management.base import BaseCommand, CommandError

from auditoria.services import Accion, registrar
from core import rut as utilidades_rut
from cuentas import bloqueo, services
from cuentas.models import Usuario


class Command(BaseCommand):
    help = "Quita el bloqueo por intentos fallidos de un RUT o de una IP (AUT-04)."

    def add_arguments(self, parser):
        grupo = parser.add_mutually_exclusive_group(required=True)
        grupo.add_argument("--rut", help="RUT bloqueado, con o sin puntos y guion.")
        grupo.add_argument("--ip", help="Dirección IP bloqueada.")

    def handle(self, *args, **opciones):
        if opciones["ip"]:
            try:
                ip = str(ipaddress.ip_address(opciones["ip"]))
            except ValueError:
                raise CommandError("La dirección IP no es válida.") from None
            bloqueo.desbloquear_ip(ip)
            registrar(Accion.DESBLOQUEO, ip=ip, detalle="IP, por comando")
            self.stdout.write(self.style.SUCCESS(f"Se desbloqueó la IP {ip}."))
            return

        if not utilidades_rut.es_valido(opciones["rut"]):
            raise CommandError("El RUT no es válido.")
        rut = utilidades_rut.normalizar(opciones["rut"])
        usuario = Usuario.objects.select_related("empresa").filter(rut=rut).first()
        if usuario is not None:
            services.desbloquear(usuario)
        else:
            # El bloqueo también se aplica a un RUT sin cuenta.
            bloqueo.desbloquear_rut(rut)
            registrar(Accion.DESBLOQUEO, rut_intentado=rut, detalle="RUT sin cuenta, por comando")
        self.stdout.write(
            self.style.SUCCESS(f"Se desbloqueó el RUT {utilidades_rut.formatear(rut)}.")
        )
