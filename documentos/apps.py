from django.apps import AppConfig


class DocumentosConfig(AppConfig):
    name = "documentos"
    verbose_name = "Documentos"

    def ready(self):
        from documentos import comprobaciones  # noqa: F401
