import logging

from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

logger = logging.getLogger(__name__)


@require_safe
@never_cache
def salud(request):
    """Indica si la aplicación responde y llega a la base de datos, sin exponer detalles."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        logger.exception("La comprobación de salud no pudo consultar la base de datos")
        return JsonResponse({"estado": "error"}, status=503)
    return JsonResponse({"estado": "ok"})


@require_safe
def favicon(request):
    """Los navegadores piden /favicon.ico en la raíz aunque la página enlace otro ícono."""
    return redirect(static("img/favicon.ico"))


def csrf_fallido(request, reason=""):
    """Respuesta 403 propia cuando falta o no coincide el token CSRF (SEG-03)."""
    return render(request, "403_csrf.html", status=403)
