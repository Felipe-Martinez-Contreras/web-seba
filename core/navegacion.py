"""Menú y datos de la estructura común del portal y del panel (DEC-43).

Solo se listan las secciones que existen: cada etapa agrega las suyas.
"""

from django.urls import reverse

# Cada elemento: (clave, texto, nombre de la ruta, ícono). Un grupo no lleva ruta y trae
# sus elementos dentro.
_SECCIONES = {
    "cliente": [
        ("inicio", "Inicio", "portal:inicio", "house"),
        ("carpetas", "Carpetas", "portal:carpetas", "folder"),
        ("cuenta", "Mi cuenta", "cuentas:mi_cuenta", "circle-user"),
    ],
    "administrador": [
        ("inicio", "Inicio", "panel:inicio", "house"),
        ("clientes", "Clientes", "panel:clientes", "users"),
        ("solicitudes", "Solicitudes", "panel:solicitudes_consultas", "inbox"),
        ("auditoria", "Auditoría", "panel:auditoria", "history"),
        (
            "configuracion",
            "Configuración",
            [
                ("contenido", "Contenido del sitio", "panel:contenido", "globe"),
                ("cuenta", "Mi cuenta", "cuentas:mi_cuenta", "circle-user"),
            ],
            "settings",
        ),
    ],
}
_BASE = {"cliente": "base_portal.html", "administrador": "base_panel.html"}
# Largo máximo del texto de búsqueda del portal: lo aplican el campo y la vista.
BUSQUEDA_MAXIMO = 100


def inicio_de(usuario):
    """URL de inicio que corresponde al rol (AUT-03)."""
    return reverse("panel:inicio" if usuario.es_administrador else "portal:inicio")


def _elemento(clave, texto, destino, icono, seccion):
    if isinstance(destino, list):
        return {
            "texto": texto,
            "icono": icono,
            "hijos": [_elemento(*hijo, seccion) for hijo in destino],
        }
    return {"texto": texto, "url": reverse(destino), "icono": icono, "activo": clave == seccion}


def contexto(usuario, seccion):
    datos = {
        "plantilla_base": _BASE[usuario.rol],
        "menu_lateral": [_elemento(*elemento, seccion) for elemento in _SECCIONES[usuario.rol]],
        "url_cerrar_sesion": reverse("cuentas:salir"),
        "usuario_nombre": usuario.nombre,
        "menu_usuario": [("Mi cuenta", reverse("cuentas:mi_cuenta"))],
    }
    if usuario.es_administrador:
        # El buscador del panel se limita a los clientes (DISENO.md, diferencia 6).
        datos["buscador_accion"] = reverse("panel:clientes")
        datos["buscador_etiqueta"] = "Buscar clientes por RUT o razón social"
    else:
        # El del portal busca por título entre los documentos de su empresa (CLI-03).
        datos["buscador_accion"] = reverse("portal:buscar")
        datos["buscador_etiqueta"] = "Buscar documentos por título"
        datos["buscador_maximo"] = BUSQUEDA_MAXIMO
    return datos
