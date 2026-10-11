from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core import rut as utilidades_rut
from cuentas.models import Usuario
from sitio import demo


class Command(BaseCommand):
    help = (
        "Carga datos de demostración, todos marcados DEMO: contenido del sitio, una política "
        "de privacidad de prueba, dos empresas ficticias con un usuario y documentos PDF. "
        "No pisa datos existentes. Se niega a ejecutarse en producción."
    )

    def handle(self, *args, **opciones):
        # DEBUG no cuenta como permiso: `manage.py` usa la configuración de desarrollo si
        # falta DJANGO_SETTINGS_MODULE, también en un servidor.
        if not settings.DEMO_PERMITIDO:
            raise CommandError(
                "cargar_demo no se ejecuta en producción. Solo corre con DEMO_PERMITIDO=true: "
                "en desarrollo y en staging con datos ficticios."
            )
        # Los documentos de demostración quedan subidos a nombre de un administrador real.
        administrador = (
            Usuario.objects.filter(rol=Usuario.Rol.ADMINISTRADOR, is_active=True)
            .order_by("pk")
            .first()
        )
        if administrador is None:
            raise CommandError(
                "No hay ningún administrador. Créelo primero con crear_administrador."
            )
        creado = demo.cargar_contenido()
        enlaces = demo.cargar_empresas(administrador)
        if not creado and not enlaces:
            self.stdout.write("Los datos de demostración ya estaban cargados: no se cambió nada.")
            return
        for linea in creado:
            self.stdout.write(self.style.SUCCESS(linea))
        for usuario, url in enlaces:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{usuario.empresa.razon_social}: usuario {usuario.nombre}, "
                    f"RUT {utilidades_rut.formatear(usuario.rut)}"
                )
            )
            self.stdout.write(f"  Enlace de activación (un solo uso): {url}")
        self.stdout.write(
            "Todo lleva la marca DEMO y sigue listado en contenido_pendiente: "
            "son datos para probar, no para publicar."
        )
