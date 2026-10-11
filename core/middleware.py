import logging

from core.ip import ip_cliente

logger = logging.getLogger(__name__)

# Funciones del navegador que la aplicación no usa: ninguna queda permitida, ni para el
# propio origen (SEG-02). Django no trae este encabezado.
_FUNCIONES_DENEGADAS = (
    "accelerometer",
    "autoplay",
    "camera",
    "display-capture",
    "encrypted-media",
    "fullscreen",
    "geolocation",
    "gyroscope",
    "magnetometer",
    "microphone",
    "midi",
    "payment",
    "picture-in-picture",
    "publickey-credentials-get",
    "screen-wake-lock",
    "usb",
    "xr-spatial-tracking",
)
POLITICA_DE_PERMISOS = ", ".join(f"{funcion}=()" for funcion in _FUNCIONES_DENEGADAS)


class IpClienteMiddleware:
    """Calcula una vez la IP real del cliente y la deja en `request.ip_cliente`."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.ip_cliente = ip_cliente(request)
        if request.ip_cliente is None:
            # Ocurre si el servidor recibe las conexiones por un socket Unix. Los límites
            # siguen actuando, pero con un solo contador para todos los clientes.
            logger.error(
                "No se pudo determinar la IP del cliente: los límites por IP se comparten."
            )
        return self.get_response(request)


class PoliticaDePermisosMiddleware:
    """Agrega `Permissions-Policy` a todas las respuestas."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)
        respuesta.headers.setdefault("Permissions-Policy", POLITICA_DE_PERMISOS)
        return respuesta
