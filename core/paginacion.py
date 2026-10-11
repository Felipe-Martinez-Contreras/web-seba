"""Paginación común de los listados del portal y del panel (DOC-09)."""

from django.core.paginator import Paginator

POR_PAGINA = 25


def paginar(request, elementos):
    """Página pedida en `?page=`; un valor inválido o fuera de rango cae en la más cercana."""
    return Paginator(elementos, POR_PAGINA).get_page(request.GET.get("page"))
