"""Rubros en que trabaja el profesional (PUB-09, DEC-208): la sección «Áreas en las que
trabajamos» del inicio, editable desde el panel.

La foto pasa por el mismo procesamiento que las imágenes del sitio (`procesar_imagen`,
DEC-206) y se guarda igual, en `VarianteImagen`; se entrega en /imagenes/<sha256>.webp.
"""

from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.db.models import Max, Prefetch

from auditoria.models import EventoAuditoria
from auditoria.services import registrar
from sitio import imagenes, procesar_imagen
from sitio.models import Rubro, VarianteImagen
from sitio.services import BAJAR, SUBIR

Accion = EventoAuditoria.Accion

# Los de la publicidad del profesional, en su orden. `cargar_rubros` los crea sin foto.
INICIALES = (
    "Construcción",
    "Industria",
    "Logística y bodegaje",
    "Agricultura y ganadería",
    "Alimentos",
    "Transporte",
    "Comercio",
    "Servicios",
)

GRANDE, CHICA = "800", "400"


@dataclass(frozen=True)
class Foto:
    src: str
    src_chica: str
    ancho: int
    alto: int
    alt: str


def con_variantes(rubros):
    """Los rubros con los metadatos de sus variantes, en una consulta más: sin el contenido,
    que lo lee la vista que entrega la imagen."""
    return rubros.prefetch_related(
        Prefetch("variantes", queryset=VarianteImagen.objects.defer("contenido"))
    )


def foto_de(rubro):
    """La foto del rubro lista para la plantilla, o None si no tiene (o está incompleta)."""
    variantes = {variante.nombre: variante for variante in rubro.variantes.all()}
    grande, chica = variantes.get(GRANDE), variantes.get(CHICA)
    if not (grande and chica):
        return None
    return Foto(
        src=imagenes.url_de(grande),
        src_chica=imagenes.url_de(chica),
        ancho=grande.ancho,
        alto=grande.alto,
        alt=rubro.alt,
    )


def publicados():
    """Los rubros activos, en su orden, con su foto (o None)."""
    return [(rubro, foto_de(rubro)) for rubro in con_variantes(Rubro.objects.activos())]


def _procesar(archivo):
    imagenes.comprobar_peso(archivo)
    return procesar_imagen.procesar_rubro(archivo, plazo_segundos=settings.IMAGENES_PLAZO_SEGUNDOS)


def _detalle(rubro, que):
    # Texto fijo: el nombre del rubro (contenido del sitio) y qué cambió, nunca el texto
    # alternativo ni el nombre del archivo.
    return f"{rubro.nombre}: {que}"


def crear(formulario, *, actor, request=None):
    """Agrega el rubro al final de la lista, con su foto si se subió una. Rechaza la foto con
    `ImagenRechazada` antes de guardar nada."""
    archivo = formulario.cleaned_data.get("archivo")
    variantes = _procesar(archivo) if archivo else []
    with transaction.atomic():
        rubro = formulario.save(commit=False)
        rubro.orden = (Rubro.objects.aggregate(ultimo=Max("orden"))["ultimo"] or 0) + 1
        rubro.save()
        registrar(
            Accion.RUBRO_CREADO,
            request=request,
            actor=actor,
            objeto=rubro,
            detalle=_detalle(rubro, "con foto" if variantes else "sin foto"),
        )
        if variantes:
            imagenes.reemplazar_variantes(rubro, variantes, rubro=rubro)
    return rubro


def editar(formulario, *, actor, request=None):
    """Guarda el nombre, el texto alternativo y, si se subió, la foto nueva. Devuelve si algo
    cambió."""
    archivo = formulario.cleaned_data.get("archivo")
    variantes = _procesar(archivo) if archivo else []
    campos = [campo for campo in ("nombre", "alt") if campo in formulario.changed_data]
    if not campos and not variantes:
        return False
    with transaction.atomic():
        rubro = formulario.save()
        if campos:
            nombres = {"nombre": "nombre", "alt": "texto alternativo"}
            registrar(
                Accion.RUBRO_EDITADO,
                request=request,
                actor=actor,
                objeto=rubro,
                detalle=_detalle(rubro, ", ".join(nombres[campo] for campo in campos)),
            )
        if variantes:
            imagenes.reemplazar_variantes(rubro, variantes, rubro=rubro)
            registrar(
                Accion.RUBRO_FOTO_CAMBIADA,
                request=request,
                actor=actor,
                objeto=rubro,
                detalle=_detalle(rubro, "foto nueva"),
            )
    return True


def quitar_foto(rubro, *, actor, request=None):
    """Deja el rubro sin foto: la tarjeta muestra el fondo neutro con el ícono."""
    with transaction.atomic():
        borradas = rubro.variantes.all().delete()[0]
        if not borradas:
            return False
        registrar(
            Accion.RUBRO_FOTO_CAMBIADA,
            request=request,
            actor=actor,
            objeto=rubro,
            detalle=_detalle(rubro, "foto quitada"),
        )
    return True


def eliminar(rubro, *, actor, request=None):
    """Borra el rubro y su foto. Nada lo nombra, así que no hace falta conservarlo. Los demás
    quedan numerados desde 1, sin el hueco: el orden es la posición que exporta
    `exportar_contenido`."""
    with transaction.atomic():
        registrar(
            Accion.RUBRO_ELIMINADO,
            request=request,
            actor=actor,
            objeto=rubro,
            detalle=rubro.nombre,
        )
        rubro.delete()
        _numerar(list(Rubro.objects.select_for_update()))


def _numerar(rubros):
    for orden, otro in enumerate(rubros, start=1):
        otro.orden = orden
    Rubro.objects.bulk_update(rubros, ["orden"])


def mover(rubro, direccion):
    """Sube o baja el rubro un lugar y deja el orden numerado desde 1."""
    if direccion not in (SUBIR, BAJAR):
        return False
    with transaction.atomic():
        rubros = list(Rubro.objects.select_for_update())
        posicion = next(i for i, otro in enumerate(rubros) if otro.pk == rubro.pk)
        destino = posicion - 1 if direccion == SUBIR else posicion + 1
        if not 0 <= destino < len(rubros):
            return False
        rubros[posicion], rubros[destino] = rubros[destino], rubros[posicion]
        _numerar(rubros)
    return True


def cambiar_estado(rubro, activo, *, actor, request=None):
    """Muestra u oculta el rubro en el sitio. Devuelve si hubo cambio."""
    if rubro.activo == activo:
        return False
    with transaction.atomic():
        rubro.activo = activo
        rubro.save(update_fields=["activo", "actualizado_en"])
        registrar(
            Accion.RUBRO_EDITADO,
            request=request,
            actor=actor,
            objeto=rubro,
            detalle=_detalle(rubro, "activado" if activo else "desactivado"),
        )
    return True


def cargar_iniciales():
    """Crea los rubros de partida, sin foto, solo si no hay ninguno: repetirlo no duplica
    nada ni revive los que el administrador eliminó. Devuelve cuántos creó."""
    # Si dos ejecuciones coincidieran, el nombre único hace fallar la segunda entera.
    with transaction.atomic():
        if Rubro.objects.exists():
            return 0
        Rubro.objects.bulk_create(
            Rubro(nombre=nombre, orden=orden) for orden, nombre in enumerate(INICIALES, start=1)
        )
    return len(INICIALES)
