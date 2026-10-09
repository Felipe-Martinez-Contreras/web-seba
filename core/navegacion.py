"""Menú y datos de la estructura común del portal y del panel (DEC-43).

Solo se listan las secciones que existen: cada etapa agrega las suyas.
"""

from django.urls import reverse

_SECCIONES = {
    "cliente": [
        ("inicio", "Inicio", "portal:inicio", "house"),
        ("cuenta", "Mi cuenta", "cuentas:mi_cuenta", "circle-user"),
    ],
    "administrador": [
        ("inicio", "Inicio", "panel:inicio", "house"),
        ("cuenta", "Mi cuenta", "cuentas:mi_cuenta", "circle-user"),
    ],
}
_BASE = {"cliente": "base_portal.html", "administrador": "base_panel.html"}


def inicio_de(usuario):
    """URL de inicio que corresponde al rol (AUT-03)."""
    return reverse("panel:inicio" if usuario.es_administrador else "portal:inicio")


def contexto(usuario, seccion):
    return {
        "plantilla_base": _BASE[usuario.rol],
        "menu_lateral": [
            {"texto": texto, "url": reverse(ruta), "icono": icono, "activo": clave == seccion}
            for clave, texto, ruta, icono in _SECCIONES[usuario.rol]
        ],
        "url_cerrar_sesion": reverse("cuentas:salir"),
        "usuario_nombre": usuario.nombre,
        "menu_usuario": [("Mi cuenta", reverse("cuentas:mi_cuenta"))],
    }
