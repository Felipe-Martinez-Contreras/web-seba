import logging

from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@require_GET
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
