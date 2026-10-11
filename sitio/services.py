"""Contenido del sitio: datos del negocio y servicios (ADM-10), y lo que de ellos se publica."""

import re
from dataclasses import dataclass

from django.db import transaction
from django.db.models import Max
from django.utils.text import slugify

from sitio import pendientes
from sitio.models import DatosNegocio, Servicio

SUBIR = "subir"
BAJAR = "bajar"


# --- Lo que se publica ----------------------------------------------------------------


@dataclass(frozen=True)
class Contacto:
    """Datos de contacto listos para mostrarse: lo pendiente llega como cadena vacía."""

    nombre: str = ""
    telefono: str = ""
    email: str = ""
    whatsapp: str = ""
    ubicacion: str = ""
    horario: str = ""

    @property
    def hay(self):
        """Existe al menos una forma de contactar al profesional."""
        return bool(self.telefono or self.email or self.whatsapp)

    @property
    def telefono_enlace(self):
        return "tel:" + _solo_numero(self.telefono) if self.telefono else ""

    @property
    def whatsapp_enlace(self):
        numero = _solo_numero(self.whatsapp).lstrip("+")
        return f"https://wa.me/{numero}" if numero else ""

    @property
    def lineas(self):
        """Textos para el pie de página, en orden."""
        return [
            linea for linea in (self.telefono, self.email, self.ubicacion, self.horario) if linea
        ]


def _solo_numero(texto):
    return re.sub(r"[^\d+]", "", texto)


def contacto_publico(datos=None):
    """El contacto del profesional que se puede mostrar hoy (PUB-05, CLI-06)."""
    datos = datos or DatosNegocio.cargar()
    return Contacto(
        nombre=pendientes.disponible(datos.nombre_comercial),
        telefono=pendientes.disponible(datos.telefono),
        email=pendientes.disponible(datos.email_publico),
        whatsapp=pendientes.disponible(datos.whatsapp),
        ubicacion=pendientes.disponible(datos.ubicacion),
        horario=pendientes.disponible(datos.horario),
    )


def redes_sociales(datos):
    """Solo las registradas (PUB-04): lista de pares (nombre, url)."""
    redes = (
        ("Instagram", datos.instagram),
        ("LinkedIn", datos.linkedin),
        ("Facebook", datos.facebook),
    )
    return [(nombre, url) for nombre, url in redes if url]


def formularios_disponibles(datos=None):
    """Los formularios públicos exigen aceptar la política de privacidad: sin su texto no
    se muestran ni se aceptan (SEG-12)."""
    return pendientes.politica_disponible(datos or DatosNegocio.cargar())


def contenido_pendiente():
    return pendientes.listar(DatosNegocio.cargar(), list(Servicio.objects.all()))


# --- Edición desde el panel -----------------------------------------------------------


def guardar_datos(formulario):
    return formulario.save()


def _slug_libre(nombre):
    base = slugify(nombre)[:120] or "servicio"
    slug, numero = base, 2
    while Servicio.objects.filter(slug=slug).exists():
        slug = f"{base}-{numero}"
        numero += 1
    return slug


def crear_servicio(formulario):
    """Agrega el servicio al final de la lista. El identificador de su dirección se fija
    aquí y no cambia al renombrarlo: los enlaces que ya circulan siguen funcionando."""
    with transaction.atomic():
        servicio = formulario.save(commit=False)
        servicio.slug = _slug_libre(servicio.nombre)
        servicio.orden = (Servicio.objects.aggregate(ultimo=Max("orden"))["ultimo"] or 0) + 1
        servicio.save()
    return servicio


def editar_servicio(formulario):
    return formulario.save()


def mover_servicio(servicio, direccion):
    """Sube o baja el servicio un lugar y deja el orden numerado desde 1."""
    with transaction.atomic():
        servicios = list(Servicio.objects.select_for_update())
        posicion = next(i for i, otro in enumerate(servicios) if otro.pk == servicio.pk)
        destino = posicion - 1 if direccion == SUBIR else posicion + 1
        if not 0 <= destino < len(servicios):
            return False
        servicios[posicion], servicios[destino] = servicios[destino], servicios[posicion]
        for orden, otro in enumerate(servicios, start=1):
            otro.orden = orden
        Servicio.objects.bulk_update(servicios, ["orden"])
    return True


def cambiar_estado_servicio(servicio, activo):
    """Activa o desactiva. Un servicio inactivo deja de mostrarse y de ofrecerse en el
    formulario; las solicitudes que ya lo nombran no cambian. Devuelve si hubo cambio."""
    if servicio.activo == activo:
        return False
    servicio.activo = activo
    servicio.save(update_fields=["activo", "actualizado_en"])
    return True
