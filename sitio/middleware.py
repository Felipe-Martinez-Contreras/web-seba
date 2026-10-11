from sitio.paginas import SIN_ENCABEZADO

_PUBLICAS = ("sitio:", "solicitudes:")


class NoIndexarMiddleware:
    """Agrega `X-Robots-Tag: noindex` a todo lo que no es una página pública del sitio
    (PUB-07, SEG-13): portal, panel, acceso, activación, recuperación, admin de Django y
    páginas de error. Las páginas públicas deciden por sí mismas (sitio/paginas.py)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)
        coincidencia = request.resolver_match
        nombre = coincidencia.view_name if coincidencia else ""
        publica = nombre.startswith(_PUBLICAS) and respuesta.status_code == 200
        if not publica and nombre not in SIN_ENCABEZADO:
            respuesta["X-Robots-Tag"] = "noindex"
        return respuesta
