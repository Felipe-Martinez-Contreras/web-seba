"""Qué contenido falta (PUB-05, PUB-06). Una sola regla para el sitio, el panel y el comando.

Un dato falta si está vacío o lleva el marcador [COMPLETAR]: el sitio público no lo muestra.
Un dato de prueba (los que carga `cargar_demo`) sí se muestra, para poder revisar el sitio,
pero sigue pendiente. El panel y `contenido_pendiente` listan ambos casos.
"""

from dataclasses import dataclass

from django.conf import settings
from django.urls import reverse

from core import correo

MARCADOR = "[COMPLETAR]"
# Marcas de los datos de `cargar_demo`: sirven para probar, no para publicar.
MARCADOR_DE_PRUEBA = "TEXTO DE PRUEBA"
MARCADOR_DEMO = "(DEMO)"
# Dominio reservado para ejemplos: un correo ahí nunca es el del negocio.
DOMINIO_DEMO = "@ejemplo.test"
ES_DE_PRUEBA = "Es un dato de prueba: reemplácelo por el definitivo antes de publicar"

# Campos de DatosNegocio que deben existir antes de publicar. WhatsApp y las redes sociales
# son opcionales (sección 6) y no cuentan.
CAMPOS_REQUERIDOS = (
    "nombre_comercial",
    "titular",
    "bajada",
    "presentacion",
    "telefono",
    "email_publico",
    "ubicacion",
    "horario",
)


def falta(valor):
    """Indica si el dato no se puede mostrar: vacío o con el marcador [COMPLETAR]."""
    texto = (valor or "").strip()
    return not texto or MARCADOR in texto


def de_prueba(valor):
    """El dato viene de `cargar_demo`: se muestra, pero no debe llegar a producción."""
    texto = valor or ""
    return any(marca in texto for marca in (MARCADOR_DE_PRUEBA, MARCADOR_DEMO, DOMINIO_DEMO))


def disponible(valor):
    """El dato listo para mostrarse, o una cadena vacía si está pendiente."""
    return "" if falta(valor) else valor.strip()


def politica_disponible(datos):
    """Hay un texto de política que el visitante puede leer y aceptar. El de prueba cuenta:
    con él los formularios funcionan, aunque siga listado como pendiente."""
    return not falta(datos.politica_privacidad)


@dataclass(frozen=True)
class Pendiente:
    grupo: str
    nombre: str
    detalle: str
    donde: str
    url: str = ""
    bloqueante: bool = False


def listar(datos, servicios):
    """Todo lo que falta, en el orden en que conviene completarlo."""
    url_contenido = reverse("panel:contenido")
    url_servicios = reverse("panel:servicios")
    pendientes = []
    for campo in CAMPOS_REQUERIDOS:
        valor = getattr(datos, campo)
        if falta(valor) or de_prueba(valor):
            pendientes.append(
                Pendiente(
                    "Datos del negocio",
                    str(datos._meta.get_field(campo).verbose_name).capitalize(),
                    "Sin completar" if falta(valor) else ES_DE_PRUEBA,
                    "Panel › Configuración › Contenido del sitio",
                    url_contenido,
                )
            )

    if not politica_disponible(datos):
        pendientes.append(
            Pendiente(
                "Política de privacidad",
                "Texto de la política",
                "Sin texto: los formularios públicos están ocultos",
                "Panel › Configuración › Contenido del sitio",
                url_contenido,
                bloqueante=True,
            )
        )
    elif de_prueba(datos.politica_privacidad):
        pendientes.append(
            Pendiente(
                "Política de privacidad",
                "Texto de la política",
                ES_DE_PRUEBA,
                "Panel › Configuración › Contenido del sitio",
                url_contenido,
            )
        )

    activos = [servicio for servicio in servicios if servicio.activo]
    if not activos:
        pendientes.append(
            Pendiente(
                "Servicios",
                "Servicios ofrecidos",
                "No hay ningún servicio activo",
                "Panel › Configuración › Contenido del sitio › Servicios",
                url_servicios,
            )
        )
    for servicio in activos:
        faltantes = [
            etiqueta
            for etiqueta, valor in (
                ("nombre", servicio.nombre),
                ("resumen", servicio.resumen),
                ("descripción", servicio.descripcion),
            )
            if falta(valor)
        ]
        prueba = any(
            de_prueba(valor) for valor in (servicio.nombre, servicio.resumen, servicio.descripcion)
        )
        if faltantes or prueba:
            pendientes.append(
                Pendiente(
                    "Servicios",
                    servicio.nombre,
                    "Falta: " + ", ".join(faltantes) if faltantes else ES_DE_PRUEBA,
                    "Panel › Configuración › Contenido del sitio › Servicios",
                    reverse("panel:servicio_editar", args=[servicio.pk]),
                )
            )

    if not correo.correo_configurado():
        pendientes.append(
            Pendiente(
                "Configuración",
                "Correo saliente",
                "Sin configurar: las solicitudes se guardan, pero no se notifican",
                "Variables de entorno CORREO_HOST y CORREO_REMITENTE",
            )
        )
    if not settings.NOTIFICACIONES_DESTINATARIOS:
        pendientes.append(
            Pendiente(
                "Configuración",
                "Correo que recibe las notificaciones",
                "Sin destinatarios",
                "Variable de entorno NOTIFICACIONES_DESTINATARIOS",
            )
        )
    return pendientes
