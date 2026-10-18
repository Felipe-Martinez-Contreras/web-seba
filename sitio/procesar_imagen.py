"""Validación y re-codificación de las imágenes que sube el administrador (PUB-08, DEC-205).

Nada de lo subido se sirve tal cual: se decodifica y se vuelve a codificar, sin metadatos
(EXIF con la ubicación GPS, XMP, comentarios), al tamaño que usa el sitio. Este módulo solo
usa Pillow: no toca la base de datos, así que se puede medir aparte (tiempo y memoria,
DEC-206).

Para gastar poca memoria en una máquina de 1 GB:
- el formato se comprueba por la firma de bytes y el tamaño en píxeles por la cabecera,
  antes de decodificar nada;
- una JPG se decodifica directo a escala reducida (`draft`), sin pasar por su tamaño real;
- se procesa una imagen a la vez en todo el proceso (`_UNA_A_LA_VEZ`).
"""

import io
import threading
import time
import warnings
from dataclasses import dataclass

from PIL import ExifTags, Image, ImageCms

MOTIVO_FORMATO = "El archivo no es una imagen JPG, PNG ni WebP."
MOTIVO_SOLO_PNG = "El logo debe ser una imagen PNG."
MOTIVO_DANADA = "No se pudo leer la imagen: el archivo está dañado o incompleto."
MOTIVO_GRANDE = "La imagen es muy grande; súbala más pequeña."
MOTIVO_OCUPADO = "Se está procesando otra imagen. Intente de nuevo en unos segundos."
MOTIVO_VACIO = "El archivo está vacío."

JPG, PNG, WEBP = "JPEG", "PNG", "WEBP"
_FIRMAS = ((b"\xff\xd8\xff", JPG), (b"\x89PNG\r\n\x1a\n", PNG))

# Píxeles máximos, leídos de la cabecera antes de decodificar (DEC-206). Una JPG se decodifica
# reducida, así que admite más; una PNG o una WebP se decodifica entera.
PIXELES_MAXIMOS = {JPG: 40_000_000, PNG: 16_000_000, WEBP: 4_000_000}
# Red de seguridad de Pillow para cualquier otra apertura en el proceso.
Image.MAX_IMAGE_PIXELS = max(PIXELES_MAXIMOS.values())

FOTO_LADO = 1920
FOTO_MOVIL_LADO = 960
FOTO_BYTES = 300 * 1024
FOTO_MOVIL_BYTES = 100 * 1024
_CALIDADES = (80, 65, 50)

LOGO_MINIMO = 180
LOGO_MAXIMO = 2048
SIMBOLO_LADO = 128
AZUL_MARINO = (27, 45, 79)
# Proporción del cuadro que ocupa el símbolo en el favicon, como el original.
_ICONO_MARGEN = 0.8

# Cómo enderezar la foto según la orientación que anotó la cámara (EXIF 274).
_ENDEREZAR = {
    2: Image.Transpose.FLIP_LEFT_RIGHT,
    3: Image.Transpose.ROTATE_180,
    4: Image.Transpose.FLIP_TOP_BOTTOM,
    5: Image.Transpose.TRANSPOSE,
    6: Image.Transpose.ROTATE_270,
    7: Image.Transpose.TRANSVERSE,
    8: Image.Transpose.ROTATE_90,
}

_UNA_A_LA_VEZ = threading.Lock()
_ESPERA_SEGUNDOS = 5


class ImagenRechazada(ValueError):
    def __init__(self, motivo):
        super().__init__(motivo)
        self.motivo = motivo


@dataclass(frozen=True)
class Variante:
    nombre: str
    tipo_mime: str
    ancho: int
    alto: int
    contenido: bytes


class _Plazo:
    """Corta el procesamiento entre pasos cuando pasa el plazo. Un paso de Pillow no se
    puede interrumpir, pero ninguno dura más que una fracción del total."""

    def __init__(self, segundos):
        self.limite = time.monotonic() + segundos

    def comprobar(self):
        if time.monotonic() > self.limite:
            raise ImagenRechazada(MOTIVO_GRANDE)


def formato_de(cabecera):
    """Formato según la firma de bytes, nunca según la extensión ni el tipo declarado."""
    for firma, formato in _FIRMAS:
        if cabecera.startswith(firma):
            return formato
    if len(cabecera) >= 12 and cabecera[:4] == b"RIFF" and cabecera[8:12] == b"WEBP":
        return WEBP
    return None


def _abrir(archivo, formatos_admitidos):
    """Abre la imagen sin decodificarla: Pillow solo lee la cabecera."""
    archivo.seek(0)
    cabecera = archivo.read(16)
    if not cabecera:
        raise ImagenRechazada(MOTIVO_VACIO)
    formato = formato_de(cabecera)
    if formato is None:
        raise ImagenRechazada(MOTIVO_FORMATO)
    if formato not in formatos_admitidos:
        raise ImagenRechazada(MOTIVO_SOLO_PNG if formatos_admitidos == (PNG,) else MOTIVO_FORMATO)
    archivo.seek(0)
    # `formats` impide que Pillow pruebe otro decodificador que el de la firma.
    imagen = Image.open(archivo, formats=[formato])
    ancho, alto = imagen.size
    if ancho * alto > PIXELES_MAXIMOS[formato]:
        imagen.close()
        raise ImagenRechazada(MOTIVO_GRANDE)
    return imagen


def _a_srgb(imagen, perfil):
    """Convierte a sRGB si la foto trae otro perfil de color (Display P3 de un celular): el
    perfil no se guarda, y sin convertir los colores se verían apagados."""
    if not perfil:
        return imagen
    try:
        origen = ImageCms.ImageCmsProfile(io.BytesIO(perfil))
        destino = ImageCms.createProfile("sRGB")
        return ImageCms.profileToProfile(imagen, origen, destino, outputMode=imagen.mode)
    except (ImageCms.PyCMSError, OSError, ValueError):
        return imagen


def _limpia(imagen):
    """La misma imagen sin metadatos: ninguno pasa al archivo que se guarda."""
    imagen.info = {}
    return imagen


def _webp_bajo(imagen, maximo, plazo):
    """WebP bajo el peso indicado: baja la calidad y, si no basta, reduce el tamaño en
    proporción a lo que sobra. Cada intento cuesta segundos con una fracción de CPU: una
    imagen con mucho detalle llega al peso en tres o cuatro intentos, no en doce."""
    while True:
        for calidad in _CALIDADES:
            plazo.comprobar()
            salida = io.BytesIO()
            _limpia(imagen).save(salida, "WEBP", quality=calidad, method=4, exif=b"", xmp=b"")
            peso = salida.tell()
            if peso <= maximo:
                return salida.getvalue(), imagen.size
            if peso > maximo * 2:
                # Lejos de la meta: bajar la calidad no alcanza; se reduce de inmediato.
                break
        ancho, alto = imagen.size
        if ancho <= 320 or alto <= 320:
            raise ImagenRechazada(MOTIVO_GRANDE)
        # El peso crece con la superficie: se escala por la raíz de la proporción, con margen.
        factor = max(0.5, min(0.9, (maximo / peso) ** 0.5 * 0.95))
        imagen = imagen.resize(
            (max(1, int(ancho * factor)), max(1, int(alto * factor))), Image.Resampling.LANCZOS
        )


def _con_candado(funcion):
    def envoltura(*args, **kwargs):
        if not _UNA_A_LA_VEZ.acquire(timeout=_ESPERA_SEGUNDOS):
            raise ImagenRechazada(MOTIVO_OCUPADO)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                return funcion(*args, **kwargs)
        except ImagenRechazada:
            raise
        except MemoryError as error:
            raise ImagenRechazada(MOTIVO_GRANDE) from error
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
            raise ImagenRechazada(MOTIVO_GRANDE) from error
        except (OSError, ValueError, SyntaxError, EOFError) as error:
            # Pillow informa un archivo truncado o mal formado con cualquiera de estas.
            raise ImagenRechazada(MOTIVO_DANADA) from error
        finally:
            _UNA_A_LA_VEZ.release()

    envoltura.__doc__ = funcion.__doc__
    return envoltura


@_con_candado
def procesar_foto(archivo, *, plazo_segundos):
    """Foto de fondo: JPG, PNG o WebP → WebP de hasta 1.920 px (< 300 KB) y de 960 px
    (< 100 KB). Respeta la orientación de la cámara y descarta los metadatos."""
    plazo = _Plazo(plazo_segundos)
    with _abrir(archivo, (JPG, PNG, WEBP)) as original:
        perfil = original.info.get("icc_profile")
        orientacion = original.getexif().get(ExifTags.Base.Orientation, 1)
        original.seek(0)  # una WebP o PNG animada: solo el primer cuadro
        if original.format == JPG:
            # Decodifica directo a la escala más chica que todavía cubre 1.920 px.
            original.draft("RGB", (FOTO_LADO, FOTO_LADO))
        original.load()
        plazo.comprobar()
        imagen = original
        if imagen.mode not in ("RGB", "RGBA", "L"):
            imagen = imagen.convert("RGBA")
        # La caja es cuadrada: reducir antes de girar da el mismo resultado con menos memoria.
        imagen.thumbnail((FOTO_LADO, FOTO_LADO), Image.Resampling.LANCZOS, reducing_gap=3.0)
        if imagen is original:
            # Al cerrar el archivo, Pillow descarta los píxeles de la imagen abierta.
            imagen = imagen.copy()
        plazo.comprobar()
    imagen = _a_srgb(imagen, perfil)
    if orientacion in _ENDEREZAR:
        imagen = imagen.transpose(_ENDEREZAR[orientacion])
    if imagen.mode != "RGB":
        # Una transparencia queda sobre azul marino, el mismo color del velo.
        fondo = Image.new("RGB", imagen.size, AZUL_MARINO)
        if "A" in imagen.getbands():
            fondo.paste(imagen, mask=imagen.getchannel("A"))
        else:
            fondo.paste(imagen.convert("RGB"))
        imagen = fondo
    grande, (ancho, alto) = _webp_bajo(imagen, FOTO_BYTES, plazo)
    movil = imagen.copy()
    movil.thumbnail((FOTO_MOVIL_LADO, FOTO_MOVIL_LADO), Image.Resampling.LANCZOS)
    chica, (ancho_movil, alto_movil) = _webp_bajo(movil, FOTO_MOVIL_BYTES, plazo)
    return [
        Variante("1920", "image/webp", ancho, alto, grande),
        Variante("960", "image/webp", ancho_movil, alto_movil, chica),
    ]


def _png(imagen):
    salida = io.BytesIO()
    _limpia(imagen).save(salida, "PNG", optimize=True)
    return salida.getvalue()


def _sobre_azul(simbolo, lado):
    """El símbolo centrado en un cuadro azul marino, como el favicon original."""
    cuadro = Image.new("RGBA", (lado, lado), (*AZUL_MARINO, 255))
    interior = max(1, round(lado * _ICONO_MARGEN))
    reducido = simbolo.resize((interior, interior), Image.Resampling.LANCZOS)
    desplazamiento = (lado - interior) // 2
    cuadro.alpha_composite(reducido, (desplazamiento, desplazamiento))
    return cuadro


@_con_candado
def procesar_logo(archivo, *, con_iconos, plazo_segundos):
    """Logo: PNG cuadrado de 180 a 2.048 px → símbolo de 128 px y, si `con_iconos`, el
    favicon (PNG de 32 px e ICO de 16, 32 y 48) y el apple-touch-icon de 180 px."""
    plazo = _Plazo(plazo_segundos)
    with _abrir(archivo, (PNG,)) as original:
        ancho, alto = original.size
        if ancho != alto:
            raise ImagenRechazada(
                f"El logo debe ser cuadrado: esta imagen mide {ancho} × {alto} px."
            )
        if not LOGO_MINIMO <= ancho <= LOGO_MAXIMO:
            raise ImagenRechazada(
                f"El logo debe medir entre {LOGO_MINIMO} y {LOGO_MAXIMO} px por lado: "
                f"esta imagen mide {ancho} px."
            )
        original.seek(0)
        perfil = original.info.get("icc_profile")
        logo = _a_srgb(original.convert("RGBA"), perfil)
    plazo.comprobar()
    variantes = [
        Variante(
            "simbolo",
            "image/png",
            SIMBOLO_LADO,
            SIMBOLO_LADO,
            _png(logo.resize((SIMBOLO_LADO, SIMBOLO_LADO), Image.Resampling.LANCZOS)),
        )
    ]
    if con_iconos:
        plazo.comprobar()
        variantes.append(Variante("favicon32", "image/png", 32, 32, _png(_sobre_azul(logo, 32))))
        apple = _sobre_azul(logo, 180).convert("RGB")
        variantes.append(Variante("apple180", "image/png", 180, 180, _png(apple)))
        ico = io.BytesIO()
        _limpia(_sobre_azul(logo, 48)).save(ico, "ICO", sizes=[(16, 16), (32, 32), (48, 48)])
        variantes.append(Variante("ico", "image/x-icon", 48, 48, ico.getvalue()))
    plazo.comprobar()
    return variantes
