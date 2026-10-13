from django.apps import AppConfig


class SolicitudesConfig(AppConfig):
    name = "solicitudes"
    verbose_name = "Solicitudes"

    def ready(self):
        from solicitudes import comprobaciones  # noqa: F401
