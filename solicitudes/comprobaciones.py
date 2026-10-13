"""Comprobaciones de la configuración de las solicitudes (`manage.py check`)."""

from django.core.checks import Error, register

from solicitudes import services


@register()
def plazo_de_conservacion(app_configs, **kwargs):
    try:
        services.plazo_de_retencion()
    except services.PlazoInvalido as error:
        return [
            Error(
                str(error),
                hint="Use 30 o más. El valor por omisión es 365, el plazo de la política.",
                id="solicitudes.E001",
            )
        ]
    return []
