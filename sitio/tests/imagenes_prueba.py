"""Imágenes reales, generadas con Pillow, para las pruebas de las imágenes del sitio."""

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

# Coordenadas GPS de ejemplo: no deben llegar nunca a una imagen publicada.
GPS = {1: "S", 2: (33.0, 26.0, 0.0), 3: "W", 4: (70.0, 39.0, 0.0)}


def _exif(orientacion=None, gps=True):
    exif = Image.Exif()
    exif[0x010F] = "Fabricante de prueba"  # Make
    exif[0x0110] = "Celular de prueba"  # Model
    if orientacion:
        exif[0x0112] = orientacion
    if gps:
        exif[0x8825] = GPS
    return exif.tobytes()


def foto(ancho=1200, alto=800, color=(200, 120, 40)):
    """Una imagen con un degradado: no es plana, así que se comprime como algo real."""
    imagen = Image.linear_gradient("L").resize((ancho, alto))
    return Image.merge("RGB", (imagen, Image.new("L", (ancho, alto), color[1]), imagen))


def jpg(ancho=1200, alto=800, *, orientacion=None, gps=True, imagen=None):
    salida = io.BytesIO()
    (imagen or foto(ancho, alto)).save(
        salida, "JPEG", quality=90, exif=_exif(orientacion, gps), comment=b"comentario"
    )
    return salida.getvalue()


def png(ancho=1200, alto=800, *, modo="RGB", imagen=None):
    salida = io.BytesIO()
    imagen = imagen or foto(ancho, alto)
    if modo != imagen.mode:
        imagen = imagen.convert(modo)
    imagen.save(salida, "PNG", exif=_exif())
    return salida.getvalue()


def webp(ancho=1200, alto=800):
    salida = io.BytesIO()
    foto(ancho, alto).save(salida, "WEBP", quality=90, exif=_exif(), xmp=b"<x:xmpmeta/>")
    return salida.getvalue()


def logo(lado=512, *, alto=None):
    """Un escudo blanco con fondo transparente, como el logo real."""
    imagen = Image.new("RGBA", (lado, alto or lado), (0, 0, 0, 0))
    margen = lado // 5
    imagen.paste((255, 255, 255, 255), (margen, margen, lado - margen, (alto or lado) - margen))
    salida = io.BytesIO()
    imagen.save(salida, "PNG", exif=_exif())
    return salida.getvalue()


def subida(nombre, contenido, tipo="application/octet-stream"):
    return SimpleUploadedFile(nombre, contenido, content_type=tipo)


def abrir(contenido):
    imagen = Image.open(io.BytesIO(contenido))
    imagen.load()
    return imagen
