"""Página de referencia de componentes. Solo se publica en desarrollo (config/urls.py)."""

import datetime

from django import forms
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_safe

from core.validators import validar_rut


class FormularioDeReferencia(forms.Form):
    """Formulario de muestra para ver los campos con ayuda y con error."""

    rut = forms.CharField(
        label="RUT",
        help_text="Con o sin puntos y guion.",
        validators=[validar_rut],
        widget=forms.TextInput(attrs={"placeholder": "12.345.678-5"}),
    )
    clave = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    opcion = forms.ChoiceField(
        label="Lista de opciones",
        required=False,
        choices=[("", "Seleccione una opción"), ("a", "Opción A"), ("b", "Opción B")],
    )
    mensaje = forms.CharField(label="Mensaje", widget=forms.Textarea(attrs={"rows": 3}))
    casilla = forms.BooleanField(
        label="Casilla de verificación", required=False, help_text="Ayuda de la casilla."
    )


@require_http_methods(["GET", "HEAD", "POST"])
def componentes(request):
    if request.method == "POST" and request.headers.get("X-Subida") == "fragmento":
        # Destino de la zona de subida de muestra: responde un resultado y no guarda nada.
        return render(
            request,
            "componentes/resultado_subida.html",
            {
                "nombre": ", ".join(a.name for a in request.FILES.getlist("archivos"))[:150],
                "motivo": "Muestra: la página de referencia no guarda archivos.",
            },
        )
    if request.method == "POST":
        # Destino de los formularios de muestra (diálogo y cierre de sesión): no modifica nada.
        messages.success(request, "Acción de muestra recibida. No se modificó nada.")
        return redirect("referencia:componentes")

    fecha = datetime.date(2026, 1, 15)
    contexto = {
        "formulario": FormularioDeReferencia(),
        # Otro prefijo de id: los dos formularios conviven en la misma página.
        "formulario_con_errores": FormularioDeReferencia(
            {"rut": "12.345.678-9", "mensaje": ""}, auto_id="conerror_%s"
        ),
        "pagina": Paginator(range(1, 76), 25).page(2),
        "migas": [("Nivel 1", "#"), ("Nivel 2", "#"), ("Página actual", "")],
        "marca_nombre": "Nombre de muestra",
        "marca_url": "#",
        "enlaces_publicos": [("Enlace", "#"), ("Otro enlace", "#")],
        "acceso_texto": "Acceso de muestra",
        "acceso_url": "#",
        "contacto_lineas": ["Línea de contacto de muestra", "Otra línea de muestra"],
        "enlaces_pie": [("Enlace del pie", "#"), ("Otro enlace", "#")],
        "redes_sociales": [("Red de muestra", "#")],
        "menu_lateral": [
            {"texto": "Elemento activo", "url": "#", "icono": "house", "activo": True},
            {"texto": "Otro elemento", "url": "#", "icono": "folder", "activo": False},
            {
                "texto": "Grupo de muestra",
                "icono": "settings",
                "hijos": [{"texto": "Elemento del grupo", "url": "#", "activo": False}],
            },
        ],
        "url_cerrar_sesion": request.path,
        "buscador_accion": request.path,
        "buscador_etiqueta": "Buscar (muestra)",
        "usuario_nombre": "Usuario de muestra",
        "menu_usuario": [("Elemento del menú", "#"), ("Otro elemento", "#")],
        "pestanas": [
            {"texto": "Pestaña activa", "url": "#", "activa": True},
            {"texto": "Otra pestaña", "url": "#", "activa": False},
        ],
        "carpetas": [
            {"titulo": "Carpeta de muestra", "cantidad": 8, "actualizado": fecha},
            {"titulo": "Carpeta con un documento", "cantidad": 1, "actualizado": fecha},
            {"titulo": "Carpeta vacía", "cantidad": 0, "actualizado": None},
        ],
        "documentos": [
            {
                "titulo": "Documento PDF de muestra",
                "tipo": "pdf",
                "tamano": 2_516_582,
                "nuevo": True,
            },
            {"titulo": "Documento Word de muestra", "tipo": "word", "tamano": 184_320},
            {"titulo": "Planilla Excel de muestra", "tipo": "excel", "tamano": 96_256},
            {"titulo": "Presentación de muestra", "tipo": "powerpoint", "tamano": 3_355_443},
            {"titulo": "Imagen de muestra", "tipo": "imagen", "tamano": 734_003},
        ],
        "fecha": fecha,
        "filas_tabla": [
            ("Nombre de muestra A", "Tipo A", "Pendiente", "error"),
            ("Nombre de muestra B", "Tipo B", "En proceso", "info"),
            ("Nombre de muestra C", "Tipo A", "Resuelta", "exito"),
            ("Nombre de muestra D", "Tipo B", "Descartada", "neutro"),
        ],
    }
    return render(request, "core/referencia/componentes.html", contexto)


@require_safe
def error_404(request):
    return render(request, "404.html", status=404)


@require_safe
def error_500(request):
    return render(request, "500.html", status=500)
