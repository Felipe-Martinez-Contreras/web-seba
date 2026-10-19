"""Imágenes del sitio que el administrador cambia desde el panel (PUB-08, DEC-205).

Cinco ranuras: las tres fotos de fondo y el logo sobre fondo oscuro y sobre fondo claro.
Lo subido se re-codifica en `procesar_imagen` y se guarda en la base de datos; cada tamaño
se entrega en /imagenes/<sha256>.<extensión>, una URL que cambia con el contenido. Sin
imagen subida, o si la base no responde, el sitio usa la original del repositorio.
"""

import hashlib
import logging

from django.conf import settings
from django.db import DatabaseError, transaction
from django.db.models import Prefetch
from django.templatetags.static import static
from django.urls import reverse

from auditoria.models import EventoAuditoria
from auditoria.services import registrar
from sitio import fotos, procesar_imagen
from sitio.models import ImagenSitio, VarianteImagen
from sitio.procesar_imagen import ImagenRechazada

logger = logging.getLogger(__name__)

Ranura = ImagenSitio.Ranura
ORIGINALES = {
    Ranura.PORTADA: fotos.PORTADA,
    Ranura.CONTACTO: fotos.CONTACTO,
    Ranura.ACCESO: fotos.ACCESO,
}
EXTENSIONES = {
    VarianteImagen.Tipo.WEBP: "webp",
    VarianteImagen.Tipo.PNG: "png",
    VarianteImagen.Tipo.ICO: "ico",
}

# Logo original del repositorio (DEC-202).
SIMBOLO_SOBRE_OSCURO = "img/simbolo-blanco.svg"
SIMBOLO_SOBRE_CLARO = "img/simbolo.svg"


def es_foto(ranura):
    return ranura in ORIGINALES


def url_de(variante):
    return reverse("sitio:imagen", args=[f"{variante.sha256}.{EXTENSIONES[variante.tipo_mime]}"])


class Actuales:
    """Las imágenes vigentes, leídas una vez por petición. Solo metadatos: el contenido de
    cada variante lo lee la vista que la entrega."""

    def __init__(self, filas=()):
        self._filas = {fila.ranura: fila for fila in filas}

    def fila(self, ranura):
        return self._filas.get(ranura)

    def variantes(self, ranura):
        fila = self.fila(ranura)
        return {variante.nombre: variante for variante in fila.variantes.all()} if fila else {}

    def subida(self, ranura):
        return bool(self.variantes(ranura))

    def foto(self, ranura):
        original = ORIGINALES[ranura]
        fila = self.fila(ranura)
        alt = (fila.alt if fila else "") or original.alt
        variantes = self.variantes(ranura)
        grande, chica = variantes.get("1920"), variantes.get("960")
        if not (grande and chica):
            # Sin imagen subida, o con una incompleta: la original, con el texto que se haya
            # escrito para ella.
            return original.subida(
                url="", url_movil="", ancho=original.ancho, alto=original.alto, alt=alt
            )
        return original.subida(
            url=url_de(grande),
            url_movil=url_de(chica),
            ancho=grande.ancho,
            alto=grande.alto,
            alt=alt,
        )

    def _simbolo(self, ranura):
        variante = self.variantes(ranura).get("simbolo")
        return url_de(variante) if variante else ""

    @property
    def simbolo_sobre_oscuro(self):
        """El símbolo del encabezado, el pie y las barras laterales (azul marino)."""
        return self._simbolo(Ranura.LOGO_FONDO_OSCURO) or static(SIMBOLO_SOBRE_OSCURO)

    @property
    def simbolo_sobre_claro(self):
        """El de las pantallas de acceso (blanco). Si solo se subió el logo para fondo
        oscuro, ese mismo va sobre un cuadro azul marino (`simbolo_con_fondo`)."""
        return (
            self._simbolo(Ranura.LOGO_FONDO_CLARO)
            or self._simbolo(Ranura.LOGO_FONDO_OSCURO)
            or static(SIMBOLO_SOBRE_CLARO)
        )

    @property
    def simbolo_con_fondo(self):
        return not self._simbolo(Ranura.LOGO_FONDO_CLARO) and bool(
            self._simbolo(Ranura.LOGO_FONDO_OSCURO)
        )

    @property
    def iconos(self):
        """Favicon y apple-touch-icon generados desde el logo subido. Vacío: los originales."""
        variantes = self.variantes(Ranura.LOGO_FONDO_OSCURO)
        nombres = ("ico", "favicon32", "apple180")
        if not all(nombre in variantes for nombre in nombres):
            return {}
        return {nombre: url_de(variantes[nombre]) for nombre in nombres}

    @property
    def foto_acceso(self):
        return self.foto(Ranura.ACCESO)


def cargar():
    """Las imágenes vigentes. Si la base falla, las originales: el sitio sigue mostrándose."""
    try:
        filas = list(
            ImagenSitio.objects.prefetch_related(
                Prefetch("variantes", queryset=VarianteImagen.objects.defer("contenido"))
            )
        )
    except DatabaseError:
        logger.exception("No se pudieron leer las imágenes del sitio; se usan las originales")
        filas = []
    return Actuales(filas)


def de_la_peticion(request):
    """Una sola lectura por petición, la comparten las vistas y el procesador de contexto."""
    if not hasattr(request, "_imagenes_sitio"):
        request._imagenes_sitio = cargar()
    return request._imagenes_sitio


def tamano_maximo():
    return settings.IMAGENES_TAMANO_MAXIMO_MB * 1024 * 1024


def comprobar_peso(archivo):
    """Rechaza el archivo por su peso, antes de abrirlo."""
    if archivo.size > tamano_maximo():
        raise ImagenRechazada(
            f"La imagen pesa más de {settings.IMAGENES_TAMANO_MAXIMO_MB} MB; súbala más pequeña."
        )


def _procesar(ranura, archivo):
    comprobar_peso(archivo)
    plazo = settings.IMAGENES_PLAZO_SEGUNDOS
    if es_foto(ranura):
        return procesar_imagen.procesar_foto(archivo, plazo_segundos=plazo)
    return procesar_imagen.procesar_logo(
        archivo, con_iconos=ranura == Ranura.LOGO_FONDO_OSCURO, plazo_segundos=plazo
    )


def reemplazar_variantes(dueno, variantes, **relacion):
    """Cambia las variantes guardadas de `dueno` (una imagen del sitio o un rubro) por las
    recién procesadas. `relacion` es el campo que las une a él: `imagen=` o `rubro=`."""
    dueno.variantes.all().delete()
    VarianteImagen.objects.bulk_create(
        VarianteImagen(
            **relacion,
            nombre=variante.nombre,
            tipo_mime=variante.tipo_mime,
            sha256=hashlib.sha256(variante.contenido).hexdigest(),
            ancho=variante.ancho,
            alto=variante.alto,
            contenido=variante.contenido,
        )
        for variante in variantes
    )


def cambiar(ranura, *, archivo=None, alt="", actor, request=None):
    """Guarda una imagen nueva y su texto alternativo, o solo el texto. Devuelve si algo
    cambió. Rechaza con `ImagenRechazada` y el motivo en palabras del usuario."""
    variantes = _procesar(ranura, archivo) if archivo else []
    alt = " ".join(alt.split()) if es_foto(ranura) else ""
    with transaction.atomic():
        fila = ImagenSitio.objects.select_for_update().filter(ranura=ranura).first()
        alt_vigente = (fila.alt if fila else "") or (
            ORIGINALES[ranura].alt if es_foto(ranura) else ""
        )
        cambia_alt = es_foto(ranura) and alt != alt_vigente
        if not variantes and not cambia_alt:
            return False
        if fila is None:
            fila = ImagenSitio(ranura=ranura)
        fila.alt = alt
        fila.save()
        if variantes:
            reemplazar_variantes(fila, variantes, imagen=fila)
        # Un texto fijo: ni el nombre del archivo ni el texto alternativo.
        que = "imagen nueva" if variantes else "texto alternativo"
        registrar(
            EventoAuditoria.Accion.IMAGEN_CAMBIADA,
            request=request,
            actor=actor,
            objeto=fila,
            detalle=f"{fila.get_ranura_display()}: {que}",
        )
    return True


def restaurar(ranura, *, actor, request=None):
    """Vuelve a la imagen original del repositorio y a su texto alternativo."""
    with transaction.atomic():
        fila = ImagenSitio.objects.select_for_update().filter(ranura=ranura).first()
        if fila is None:
            return False
        detalle = fila.get_ranura_display()
        registrar(
            EventoAuditoria.Accion.IMAGEN_RESTAURADA,
            request=request,
            actor=actor,
            objeto=fila,
            detalle=detalle,
        )
        fila.delete()
    return True
