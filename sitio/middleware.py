from django.http import Http404, HttpResponseNotFound

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


class ImagenesMiddleware:
    """Entrega /imagenes/… antes de la sesión, la autenticación y el CSRF, como WhiteNoise
    entrega los estáticos (DEC-205). La respuesta es la misma para todos: así no lleva
    `Vary: Cookie` ni `Set-Cookie`, y Cloudflare la guarda en caché."""

    PREFIJO = "/imagenes/"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path_info.startswith(self.PREFIJO):
            return self.get_response(request)
        from sitio.views import imagen

        try:
            return imagen(request, request.path_info.removeprefix(self.PREFIJO))
        except Http404:
            # Sin la página 404 del sitio: necesita la sesión, que aquí no se cargó.
            respuesta = HttpResponseNotFound(
                "No encontrada.", content_type="text/plain; charset=utf-8"
            )
            respuesta["X-Robots-Tag"] = "noindex"
            return respuesta
