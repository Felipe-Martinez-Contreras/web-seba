from core.ip import ip_cliente


class IpClienteMiddleware:
    """Calcula una vez la IP real del cliente y la deja en `request.ip_cliente`."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.ip_cliente = ip_cliente(request)
        return self.get_response(request)
