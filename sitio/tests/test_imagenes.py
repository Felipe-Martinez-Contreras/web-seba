"""Imágenes del sitio: validación, re-codificación, entrega y respaldo (PUB-08, DEC-205)."""

import io
import re
import struct
import zlib

import pytest
from django.db import DatabaseError
from PIL import Image

from auditoria.models import EventoAuditoria
from sitio import fotos, imagenes, procesar_imagen
from sitio.models import ImagenSitio, VarianteImagen
from sitio.procesar_imagen import ImagenRechazada
from sitio.tests import imagenes_prueba as prueba

Ranura = imagenes.Ranura
PLAZO = 60


def _archivo(contenido):
    return io.BytesIO(contenido)


def _foto(contenido):
    return procesar_imagen.procesar_foto(_archivo(contenido), plazo_segundos=PLAZO)


def _logo(contenido, con_iconos=True):
    return procesar_imagen.procesar_logo(
        _archivo(contenido), con_iconos=con_iconos, plazo_segundos=PLAZO
    )


def _sin_metadatos(contenido):
    imagen = prueba.abrir(contenido)
    assert not imagen.getexif(), "quedó EXIF"
    for clave in ("exif", "xmp", "XML:com.adobe.xmp", "comment", "icc_profile"):
        assert clave not in imagen.info, clave
    assert b"Celular de prueba" not in contenido and b"Fabricante de prueba" not in contenido
    assert b"xmpmeta" not in contenido and b"comentario" not in contenido


def _png_con_cabecera(ancho, alto):
    """Una PNG cuya cabecera declara el tamaño indicado, con un solo píxel de datos: se
    rechaza por la cabecera, sin decodificar nada."""
    cabecera = struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0)

    def bloque(tipo, datos):
        return (
            struct.pack(">I", len(datos))
            + tipo
            + datos
            + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + bloque(b"IHDR", cabecera)
        + bloque(b"IDAT", zlib.compress(b"\x00\x00\x00\x00"))
        + bloque(b"IEND", b"")
    )


# --- Formato por contenido --------------------------------------------------------------


@pytest.mark.parametrize(
    "contenido",
    [
        b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        b"<!doctype html><html><script>alert(1)</script></html>",
        b"GIF89a\x01\x00\x01\x00\x00\x00\x00;",
        b"MZ\x90\x00ejecutable",
        b"%PDF-1.7 documento",
    ],
    ids=["svg", "html", "gif", "ejecutable", "pdf"],
)
def test_se_rechaza_lo_que_no_es_jpg_png_ni_webp_aunque_se_llame_png(contenido):
    with pytest.raises(ImagenRechazada) as rechazo:
        _foto(contenido)
    assert rechazo.value.motivo == procesar_imagen.MOTIVO_FORMATO


def test_se_rechaza_un_archivo_vacio():
    with pytest.raises(ImagenRechazada) as rechazo:
        _foto(b"")
    assert rechazo.value.motivo == procesar_imagen.MOTIVO_VACIO


def test_se_rechaza_una_imagen_truncada():
    with pytest.raises(ImagenRechazada) as rechazo:
        _foto(prueba.jpg()[:2000])
    assert rechazo.value.motivo == procesar_imagen.MOTIVO_DANADA


def test_el_formato_sale_de_la_firma_y_no_del_nombre():
    assert procesar_imagen.formato_de(prueba.jpg()[:16]) == "JPEG"
    assert procesar_imagen.formato_de(prueba.png()[:16]) == "PNG"
    assert procesar_imagen.formato_de(prueba.webp()[:16]) == "WEBP"
    assert procesar_imagen.formato_de(b"RIFF\x00\x00\x00\x00WAVEfmt ") is None


def test_el_logo_solo_admite_png():
    with pytest.raises(ImagenRechazada) as rechazo:
        _logo(prueba.jpg(512, 512))
    assert rechazo.value.motivo == procesar_imagen.MOTIVO_SOLO_PNG


def test_el_logo_debe_ser_cuadrado_y_de_tamano_razonable():
    with pytest.raises(ImagenRechazada, match="cuadrado"):
        _logo(prueba.logo(512, alto=400))
    with pytest.raises(ImagenRechazada, match="entre 180 y 2048"):
        _logo(prueba.logo(100))


# --- Imágenes "bomba" -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ancho", "alto"), [(4001, 4000), (20_000, 20_000), (60_000, 60_000)], ids=str
)
def test_una_png_gigante_se_rechaza_por_la_cabecera_sin_decodificarla(ancho, alto):
    with pytest.raises(ImagenRechazada) as rechazo:
        _foto(_png_con_cabecera(ancho, alto))
    assert rechazo.value.motivo == procesar_imagen.MOTIVO_GRANDE


def test_los_limites_de_pixeles_son_los_medidos():
    """DEC-206: una JPG se decodifica reducida y admite más píxeles que una PNG o una WebP."""
    assert procesar_imagen.PIXELES_MAXIMOS == {
        "JPEG": 40_000_000,
        "PNG": 16_000_000,
        "WEBP": 4_000_000,
    }
    assert Image.MAX_IMAGE_PIXELS == 40_000_000


def test_una_webp_sobre_su_limite_se_rechaza():
    salida = io.BytesIO()
    Image.new("RGB", (2100, 2000), (90, 90, 90)).save(salida, "WEBP")
    with pytest.raises(ImagenRechazada) as rechazo:
        _foto(salida.getvalue())
    assert rechazo.value.motivo == procesar_imagen.MOTIVO_GRANDE


def test_si_se_acaba_el_plazo_el_motivo_es_claro_y_no_un_error():
    with pytest.raises(ImagenRechazada) as rechazo:
        procesar_imagen.procesar_foto(_archivo(prueba.jpg()), plazo_segundos=-1)
    assert rechazo.value.motivo == "La imagen es muy grande; súbala más pequeña."


def test_una_falta_de_memoria_se_informa_como_imagen_muy_grande(monkeypatch):
    def sin_memoria(*args, **kwargs):
        raise MemoryError

    monkeypatch.setattr(Image.Image, "thumbnail", sin_memoria)
    with pytest.raises(ImagenRechazada) as rechazo:
        _foto(prueba.jpg())
    assert rechazo.value.motivo == procesar_imagen.MOTIVO_GRANDE


def test_se_procesa_una_imagen_a_la_vez(monkeypatch):
    monkeypatch.setattr(procesar_imagen, "_ESPERA_SEGUNDOS", 0.01)
    procesar_imagen._UNA_A_LA_VEZ.acquire()
    try:
        with pytest.raises(ImagenRechazada) as rechazo:
            _foto(prueba.jpg())
    finally:
        procesar_imagen._UNA_A_LA_VEZ.release()
    assert rechazo.value.motivo == procesar_imagen.MOTIVO_OCUPADO
    assert _foto(prueba.jpg())


# --- Re-codificación --------------------------------------------------------------------


@pytest.mark.parametrize("contenido", [prueba.jpg(), prueba.png(), prueba.webp()], ids=str)
def test_toda_foto_sale_en_webp_sin_metadatos_y_dentro_de_los_limites(contenido):
    grande, chica = _foto(contenido)
    assert (grande.nombre, chica.nombre) == ("1920", "960")
    for variante, lado, peso in ((grande, 1920, 300 * 1024), (chica, 960, 100 * 1024)):
        assert variante.tipo_mime == "image/webp"
        assert variante.contenido[:4] == b"RIFF" and variante.contenido[8:12] == b"WEBP"
        assert max(variante.ancho, variante.alto) <= lado
        assert len(variante.contenido) <= peso
        imagen = prueba.abrir(variante.contenido)
        assert imagen.size == (variante.ancho, variante.alto)
        _sin_metadatos(variante.contenido)


def test_una_foto_grande_se_reduce_a_1920_px_de_ancho():
    grande, chica = _foto(prueba.jpg(4000, 3000))
    assert (grande.ancho, grande.alto) == (1920, 1440)
    assert (chica.ancho, chica.alto) == (960, 720)


def test_una_foto_chica_no_se_agranda():
    grande, _ = _foto(prueba.jpg(800, 500))
    assert (grande.ancho, grande.alto) == (800, 500)


def test_una_foto_vertical_de_celular_queda_derecha():
    """El celular guarda la foto acostada y anota que hay que girarla (orientación 6)."""
    acostada = prueba.foto(1600, 1200)
    acostada.paste((255, 0, 0), (0, 0, 200, 200))  # marca roja en la esquina superior izquierda
    grande, _ = _foto(prueba.jpg(imagen=acostada, orientacion=6))
    assert (grande.ancho, grande.alto) == (1200, 1600)
    imagen = prueba.abrir(grande.contenido).convert("RGB")
    # Girada 90° a la derecha, la marca queda arriba a la derecha.
    rojo, verde, azul = imagen.getpixel((grande.ancho - 40, 40))
    assert rojo > 180 and verde < 90 and azul < 90


def test_una_foto_con_transparencia_queda_sobre_azul_marino():
    transparente = Image.new("RGBA", (800, 600), (0, 0, 0, 0))
    grande, _ = _foto(prueba.png(imagen=transparente, modo="RGBA"))
    rojo, verde, azul = prueba.abrir(grande.contenido).convert("RGB").getpixel((400, 300))
    assert abs(rojo - 27) < 8 and abs(verde - 45) < 8 and abs(azul - 79) < 8


def test_el_logo_genera_simbolo_favicon_ico_y_apple_touch_icon():
    variantes = {variante.nombre: variante for variante in _logo(prueba.logo())}
    assert set(variantes) == {"simbolo", "favicon32", "apple180", "ico"}
    simbolo = prueba.abrir(variantes["simbolo"].contenido)
    assert simbolo.size == (128, 128) and simbolo.mode == "RGBA"
    assert prueba.abrir(variantes["favicon32"].contenido).size == (32, 32)
    apple = prueba.abrir(variantes["apple180"].contenido)
    # iOS rellena de negro la transparencia: el ícono es opaco, sobre azul marino.
    assert apple.size == (180, 180) and apple.mode == "RGB"
    assert apple.getpixel((2, 2)) == (27, 45, 79)
    ico = Image.open(io.BytesIO(variantes["ico"].contenido))
    assert ico.format == "ICO" and ico.info["sizes"] == {(16, 16), (32, 32), (48, 48)}
    for variante in variantes.values():
        assert b"Celular de prueba" not in variante.contenido
    _sin_metadatos(variantes["simbolo"].contenido)


def test_el_logo_para_fondo_claro_solo_genera_el_simbolo():
    assert [variante.nombre for variante in _logo(prueba.logo(), con_iconos=False)] == ["simbolo"]


# --- Guardado, auditoría y respaldo -----------------------------------------------------


@pytest.mark.django_db
def test_cambiar_una_foto_guarda_sus_variantes_y_registra_el_evento(administrador):
    assert imagenes.cambiar(
        Ranura.PORTADA,
        archivo=prueba.subida("IMG_2026 Juan Pérez.jpg", prueba.jpg()),
        alt="  Casco   sobre una mesa  ",
        actor=administrador,
    )
    fila = ImagenSitio.objects.get(ranura=Ranura.PORTADA)
    assert fila.alt == "Casco sobre una mesa"
    assert sorted(fila.variantes.values_list("nombre", flat=True)) == ["1920", "960"]
    evento = EventoAuditoria.objects.get(accion=EventoAuditoria.Accion.IMAGEN_CAMBIADA)
    assert evento.actor == administrador and evento.detalle == "Foto de portada: imagen nueva"
    # Ni el nombre del archivo ni el texto alternativo.
    assert "Juan" not in evento.detalle and "Casco" not in evento.detalle


@pytest.mark.django_db
def test_reemplazar_una_foto_cambia_su_url_y_borra_la_anterior(administrador):
    imagenes.cambiar(
        Ranura.CONTACTO,
        archivo=prueba.subida("a.jpg", prueba.jpg()),
        alt="Uno",
        actor=administrador,
    )
    antes = imagenes.cargar().foto(Ranura.CONTACTO).src
    imagenes.cambiar(
        Ranura.CONTACTO,
        archivo=prueba.subida("b.png", prueba.png(900, 600)),
        alt="Uno",
        actor=administrador,
    )
    despues = imagenes.cargar().foto(Ranura.CONTACTO)
    assert despues.src != antes and despues.ancho == 900
    assert VarianteImagen.objects.count() == 2


@pytest.mark.django_db
def test_cambiar_solo_el_texto_alternativo_conserva_la_foto_original(administrador):
    assert imagenes.cambiar(Ranura.ACCESO, alt="Casco amarillo", actor=administrador)
    foto = imagenes.cargar().foto(Ranura.ACCESO)
    assert foto.src == "/static/img/acceso.webp" and foto.alt == "Casco amarillo"
    evento = EventoAuditoria.objects.get()
    assert evento.detalle == "Foto de las pantallas de acceso: texto alternativo"


@pytest.mark.django_db
def test_sin_cambios_no_se_guarda_ni_se_registra_nada(administrador):
    assert not imagenes.cambiar(Ranura.PORTADA, alt=fotos.PORTADA.alt, actor=administrador)
    assert not ImagenSitio.objects.exists() and not EventoAuditoria.objects.exists()


@pytest.mark.django_db
def test_una_imagen_rechazada_no_cambia_nada(administrador):
    with pytest.raises(ImagenRechazada):
        imagenes.cambiar(
            Ranura.PORTADA,
            archivo=prueba.subida("x.png", b"<svg onload=alert(1)>"),
            alt="Otra",
            actor=administrador,
        )
    assert not ImagenSitio.objects.exists() and not EventoAuditoria.objects.exists()


@pytest.mark.django_db
def test_el_tamano_maximo_se_comprueba_antes_de_abrir_la_imagen(administrador, settings):
    settings.IMAGENES_TAMANO_MAXIMO_MB = 1
    with pytest.raises(ImagenRechazada, match="más de 1 MB"):
        imagenes.cambiar(
            Ranura.PORTADA,
            archivo=prueba.subida("grande.jpg", b"\xff\xd8\xff" + b"0" * (1024 * 1024)),
            alt="Otra",
            actor=administrador,
        )


@pytest.mark.django_db
def test_restaurar_vuelve_a_la_original_y_registra_el_evento(administrador):
    imagenes.cambiar(
        Ranura.PORTADA, archivo=prueba.subida("a.jpg", prueba.jpg()), alt="Una", actor=administrador
    )
    assert imagenes.restaurar(Ranura.PORTADA, actor=administrador)
    assert not ImagenSitio.objects.exists() and not VarianteImagen.objects.exists()
    assert imagenes.cargar().foto(Ranura.PORTADA) == fotos.PORTADA
    evento = EventoAuditoria.objects.get(accion=EventoAuditoria.Accion.IMAGEN_RESTAURADA)
    assert evento.detalle == "Foto de portada"
    assert not imagenes.restaurar(Ranura.PORTADA, actor=administrador)


@pytest.mark.django_db
def test_sin_imagenes_subidas_se_usan_las_originales():
    actuales = imagenes.cargar()
    for ranura, original in imagenes.ORIGINALES.items():
        assert actuales.foto(ranura) == original
    assert actuales.simbolo_sobre_oscuro == "/static/img/simbolo-blanco.svg"
    assert actuales.simbolo_sobre_claro == "/static/img/simbolo.svg"
    assert not actuales.simbolo_con_fondo and actuales.iconos == {}


@pytest.mark.django_db
def test_una_imagen_incompleta_cae_a_la_original(administrador):
    imagenes.cambiar(
        Ranura.PORTADA, archivo=prueba.subida("a.jpg", prueba.jpg()), alt="Una", actor=administrador
    )
    VarianteImagen.objects.filter(nombre="960").delete()
    foto = imagenes.cargar().foto(Ranura.PORTADA)
    assert foto.src == "/static/img/portada.webp" and foto.alt == "Una"


@pytest.mark.django_db
def test_si_la_base_falla_se_usan_las_originales(monkeypatch, caplog):
    def falla(*args, **kwargs):
        raise DatabaseError("sin conexión")

    monkeypatch.setattr(ImagenSitio.objects, "prefetch_related", falla)
    actuales = imagenes.cargar()
    assert actuales.foto(Ranura.PORTADA) == fotos.PORTADA
    assert "se usan las originales" in caplog.text


@pytest.mark.django_db
def test_el_logo_subido_reemplaza_simbolo_e_iconos(administrador):
    imagenes.cambiar(
        Ranura.LOGO_FONDO_OSCURO, archivo=prueba.subida("l.png", prueba.logo()), actor=administrador
    )
    actuales = imagenes.cargar()
    assert re.fullmatch(r"/imagenes/[0-9a-f]{64}\.png", actuales.simbolo_sobre_oscuro)
    # Sin logo para fondo claro, el de fondo oscuro va sobre un cuadro azul marino.
    assert actuales.simbolo_sobre_claro == actuales.simbolo_sobre_oscuro
    assert actuales.simbolo_con_fondo
    assert set(actuales.iconos) == {"ico", "favicon32", "apple180"}
    assert actuales.iconos["ico"].endswith(".ico")
    imagenes.cambiar(
        Ranura.LOGO_FONDO_CLARO,
        archivo=prueba.subida("c.png", prueba.logo(300)),
        actor=administrador,
    )
    actuales = imagenes.cargar()
    assert actuales.simbolo_sobre_claro != actuales.simbolo_sobre_oscuro
    assert not actuales.simbolo_con_fondo


# --- Entrega ----------------------------------------------------------------------------


@pytest.mark.django_db
def test_la_imagen_se_entrega_con_cache_larga_y_sin_ejecutar_nada(client, administrador):
    imagenes.cambiar(
        Ranura.PORTADA, archivo=prueba.subida("a.jpg", prueba.jpg()), alt="Una", actor=administrador
    )
    variante = VarianteImagen.objects.get(nombre="1920")
    ruta = f"/imagenes/{variante.sha256}.webp"
    respuesta = client.get(ruta)
    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "image/webp"
    assert respuesta["Cache-Control"] == "public, max-age=31536000, immutable"
    assert respuesta["ETag"] == f'"{variante.sha256}"'
    assert respuesta["X-Content-Type-Options"] == "nosniff"
    assert respuesta["Content-Security-Policy"] == "sandbox"
    assert "Set-Cookie" not in respuesta and "Vary" not in respuesta
    assert respuesta.content == bytes(variante.contenido)
    # El navegador que ya la tiene recibe un 304, sin el contenido.
    repetida = client.get(ruta, HTTP_IF_NONE_MATCH=f'"{variante.sha256}"')
    assert repetida.status_code == 304 and repetida.content == b""
    assert client.head(ruta).status_code == 200


@pytest.mark.django_db
def test_una_imagen_inexistente_o_con_otra_extension_responde_404(client, administrador):
    imagenes.cambiar(
        Ranura.PORTADA, archivo=prueba.subida("a.jpg", prueba.jpg()), alt="Una", actor=administrador
    )
    sha = VarianteImagen.objects.get(nombre="1920").sha256
    for ruta in (
        f"/imagenes/{sha}.png",
        f"/imagenes/{sha}.svg",
        f"/imagenes/{'0' * 64}.webp",
        "/imagenes/portada.webp",
        f"/imagenes/{sha.upper()}.webp",
    ):
        assert client.get(ruta).status_code == 404, ruta
    assert client.post(f"/imagenes/{sha}.webp").status_code == 405


@pytest.mark.django_db
def test_el_sitio_muestra_la_foto_subida_con_su_velo_y_su_texto(client, negocio, administrador):
    imagenes.cambiar(
        Ranura.PORTADA,
        archivo=prueba.subida("a.jpg", prueba.jpg(3000, 2000)),
        alt="Grúa sobre un edificio en obra",
        actor=administrador,
    )
    foto = imagenes.cargar().foto(Ranura.PORTADA)
    contenido = client.get("/").content.decode()
    assert f'src="{foto.src}" srcset="{foto.src_movil} 960w, {foto.src} 1920w"' in contenido
    assert 'width="1920" height="1280"' in contenido
    assert 'alt="Grúa sobre un edificio en obra"' in contenido
    assert 'class="velo ' in contenido and "/static/img/portada.webp" not in contenido
    assert f'<link rel="preload" as="image" href="{foto.src}"' in contenido
    assert f'content="http://testserver{foto.src_movil}"' in contenido
    # La foto se entrega desde el mismo dominio: la CSP sigue con img-src 'self'.
    assert foto.src.startswith("/imagenes/")


@pytest.mark.django_db
def test_el_acceso_y_la_marca_usan_las_imagenes_subidas(client, negocio, administrador):
    imagenes.cambiar(
        Ranura.ACCESO,
        archivo=prueba.subida("a.webp", prueba.webp()),
        alt="Pasillo de una planta",
        actor=administrador,
    )
    imagenes.cambiar(
        Ranura.LOGO_FONDO_OSCURO, archivo=prueba.subida("l.png", prueba.logo()), actor=administrador
    )
    actuales = imagenes.cargar()
    acceso = client.get("/acceso/").content.decode()
    assert f'src="{actuales.foto_acceso.src}"' in acceso and 'alt="Pasillo de una planta"' in acceso
    assert f'<span class="marca-cuadro"><img src="{actuales.simbolo_sobre_claro}"' in acceso
    inicio = client.get("/").content.decode()
    assert f'src="{actuales.simbolo_sobre_oscuro}" alt="" width="32" height="32"' in inicio
    assert f'<link rel="icon" href="{actuales.iconos["ico"]}"' in inicio
    assert f'<link rel="apple-touch-icon" href="{actuales.iconos["apple180"]}">' in inicio
    assert "favicon.svg" not in inicio
    favicon = client.get("/favicon.ico")
    assert favicon.status_code == 302 and favicon["Location"] == actuales.iconos["ico"]


@pytest.mark.django_db
def test_una_pagina_lee_las_imagenes_una_sola_vez(client, negocio):
    """Las vistas y el procesador de contexto comparten la lectura de la petición."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with CaptureQueriesContext(connection) as consultas:
        client.get("/")
    lecturas = [c["sql"] for c in consultas.captured_queries if "sitio_imagensitio" in c["sql"]]
    assert len(lecturas) == 1


@pytest.mark.parametrize("modo", ["P", "L", "CMYK"])
def test_una_foto_en_paleta_grises_o_cmyk_sale_en_rgb(modo):
    imagen = prueba.foto(800, 600).convert(modo)
    salida = io.BytesIO()
    imagen.save(salida, "JPEG" if modo == "CMYK" else "PNG")
    grande, _ = _foto(salida.getvalue())
    assert prueba.abrir(grande.contenido).mode == "RGB"


def test_una_foto_con_perfil_de_color_se_convierte_y_el_perfil_no_se_guarda():
    from PIL import ImageCms

    perfil = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    salida = io.BytesIO()
    prueba.foto(800, 600).save(salida, "JPEG", icc_profile=perfil)
    grande, _ = _foto(salida.getvalue())
    assert "icc_profile" not in prueba.abrir(grande.contenido).info
    # Un perfil dañado no impide publicar la foto: se usa tal cual.
    salida = io.BytesIO()
    prueba.foto(800, 600).save(salida, "JPEG", icc_profile=b"no es un perfil")
    assert _foto(salida.getvalue())


def test_una_foto_con_mucho_detalle_se_reduce_hasta_quedar_bajo_300_kb():
    """Ruido puro: ni con la calidad más baja cabe en 300 KB a 1.920 px."""
    ruido = Image.merge(
        "RGB", [Image.effect_noise((1920, 1280), 90).convert("L") for _ in range(3)]
    )
    salida = io.BytesIO()
    ruido.save(salida, "PNG")
    grande, chica = _foto(salida.getvalue())
    assert grande.ancho < 1920 and len(grande.contenido) <= 300 * 1024
    assert len(chica.contenido) <= 100 * 1024


def test_si_ni_reduciendo_cabe_se_rechaza(monkeypatch):
    monkeypatch.setattr(procesar_imagen, "FOTO_BYTES", 10)
    with pytest.raises(ImagenRechazada) as rechazo:
        _foto(prueba.jpg(800, 600))
    assert rechazo.value.motivo == procesar_imagen.MOTIVO_GRANDE
