"""Rubros: procesamiento de la foto, sección del inicio y rubros de partida (PUB-09, DEC-208)."""

import io
import re

import pytest
from django.core.management import call_command
from django.db import IntegrityError, connection
from django.test.utils import CaptureQueriesContext

from sitio import imagenes, procesar_imagen, rubros
from sitio.models import Rubro, VarianteImagen
from sitio.procesar_imagen import ImagenRechazada
from sitio.tests import imagenes_prueba as prueba
from sitio.tests.test_imagenes import _png_con_cabecera, _sin_metadatos

PLAZO = 60
TITULO = "Áreas en las que trabajamos"


def _procesar(contenido):
    return procesar_imagen.procesar_rubro(io.BytesIO(contenido), plazo_segundos=PLAZO)


def _con_foto(nombre="Construcción", orden=1, alt="Grúa torre sobre una obra.", **campos):
    rubro = Rubro.objects.create(nombre=nombre, orden=orden, alt=alt, **campos)
    variantes = _procesar(prueba.jpg(1600, 1000))
    imagenes.reemplazar_variantes(rubro, variantes, rubro=rubro)
    return rubro


# --- Procesamiento -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "contenido",
    [prueba.jpg(2400, 1200), prueba.png(1600, 1600), prueba.webp(1200, 900)],
    ids=["jpg-panoramica", "png-cuadrada", "webp-4-3"],
)
def test_la_foto_se_recorta_a_4_3_en_800_y_400_px_bajo_su_peso_y_sin_metadatos(contenido):
    grande, chica = _procesar(contenido)
    assert (grande.nombre, grande.tipo_mime) == ("800", "image/webp")
    assert (grande.ancho, grande.alto) == (800, 600)
    assert (chica.nombre, chica.ancho, chica.alto) == ("400", 400, 300)
    assert len(grande.contenido) <= procesar_imagen.RUBRO_BYTES
    assert len(chica.contenido) <= procesar_imagen.RUBRO_CHICA_BYTES
    for variante in (grande, chica):
        assert prueba.abrir(variante.contenido).size == (variante.ancho, variante.alto)
        _sin_metadatos(variante.contenido)
    assert b"GPS" not in grande.contenido


def test_el_recorte_conserva_el_centro_de_la_foto():
    panoramica = prueba.foto(2000, 750)
    panoramica.paste((255, 0, 0), (0, 0, 300, 750))  # franja roja a la izquierda: se recorta
    panoramica.paste((0, 0, 255), (950, 300, 1050, 450))  # marca azul al centro: queda
    grande, _ = _procesar(prueba.jpg(imagen=panoramica))
    imagen = prueba.abrir(grande.contenido).convert("RGB")
    rojo, _, azul = imagen.getpixel((400, 300))
    assert azul > 180 and rojo < 90
    rojo, verde, _ = imagen.getpixel((5, 300))
    assert not (rojo > 180 and verde < 90)


def test_una_foto_chica_se_recorta_sin_agrandarse():
    grande, chica = _procesar(prueba.jpg(600, 600))
    assert (grande.ancho, grande.alto) == (600, 450)
    assert (chica.ancho, chica.alto) == (400, 300)


def test_una_foto_vertical_de_celular_queda_derecha_antes_de_recortar():
    """El celular la guarda acostada y anota que hay que girarla 90° a la derecha."""
    acostada = prueba.foto(1600, 1200)
    acostada.paste((0, 0, 255), (0, 0, 1600, 150))  # franja azul en el borde de arriba
    grande, _ = _procesar(prueba.jpg(imagen=acostada, orientacion=6))
    assert (grande.ancho, grande.alto) == (800, 600)
    imagen = prueba.abrir(grande.contenido).convert("RGB")
    # Girada a la derecha, el borde de arriba queda a la derecha, y el recorte 4:3 de la foto
    # ya vertical conserva todo el ancho.
    rojo, _, azul = imagen.getpixel((795, 300))
    assert azul > 180 and rojo < 90
    rojo, _, azul = imagen.getpixel((5, 300))
    assert not (azul > 180 and rojo < 90)


@pytest.mark.parametrize(
    ("contenido", "motivo"),
    [
        (b'<svg xmlns="http://www.w3.org/2000/svg"/>', procesar_imagen.MOTIVO_FORMATO),
        (b"<html><body>hola</body></html>", procesar_imagen.MOTIVO_FORMATO),
        (b"", procesar_imagen.MOTIVO_VACIO),
        (_png_con_cabecera(5000, 5000), procesar_imagen.MOTIVO_GRANDE),
        (prueba.jpg()[:300], procesar_imagen.MOTIVO_DANADA),
    ],
    ids=["svg", "html", "vacio", "demasiados-pixeles", "truncada"],
)
def test_lo_que_no_es_una_foto_valida_se_rechaza_con_su_motivo(contenido, motivo):
    with pytest.raises(ImagenRechazada) as rechazo:
        _procesar(contenido)
    assert rechazo.value.motivo == motivo


def test_si_se_acaba_el_plazo_el_motivo_es_claro():
    with pytest.raises(ImagenRechazada, match="muy grande"):
        procesar_imagen.procesar_rubro(io.BytesIO(prueba.jpg()), plazo_segundos=-1)


# --- Sitio público -----------------------------------------------------------------------


@pytest.mark.django_db
def test_sin_rubros_activos_la_seccion_no_aparece(client, negocio):
    Rubro.objects.create(nombre="Oculto", orden=1, activo=False)
    contenido = client.get("/").content.decode()
    assert TITULO not in contenido and "Oculto" not in contenido


@pytest.mark.django_db
def test_los_rubros_activos_se_muestran_en_orden_despues_de_los_servicios(
    client, negocio, servicio
):
    _con_foto("Construcción", orden=2)
    Rubro.objects.create(nombre="Industria", orden=1)
    Rubro.objects.create(nombre="Inactivo", orden=3, activo=False)
    contenido = client.get("/").content.decode()

    assert contenido.index("Nuestros servicios") < contenido.index(TITULO)
    assert contenido.index(TITULO) < contenido.index('id="contacto"')
    seccion = contenido.split(TITULO)[1].split("</section>")[0]
    assert '<ul class="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">' in seccion
    assert seccion.index("Industria") < seccion.index("Construcción")
    assert "Inactivo" not in contenido
    # Ninguna tarjeta es un enlace.
    assert "<a " not in seccion
    # Con foto: srcset de las dos variantes, alt y el nombre sobre el velo.
    rutas = re.findall(r"/imagenes/[0-9a-f]{64}\.webp", seccion)
    assert len(set(rutas)) == 2
    assert 'alt="Grúa torre sobre una obra."' in seccion
    assert 'loading="lazy"' in seccion
    assert '<h3 class="velo-nombre">Construcción</h3>' in seccion
    # Sin foto: fondo neutro con el ícono, del mismo tamaño.
    assert 'class="tarjeta-rubro tarjeta-rubro-sin-foto"' in seccion


@pytest.mark.django_db
def test_la_foto_del_rubro_se_entrega_con_cache_de_un_ano(client):
    rubro = _con_foto()
    variante = rubro.variantes.get(nombre="800")
    respuesta = client.get(f"/imagenes/{variante.sha256}.webp")
    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "image/webp"
    assert respuesta["Cache-Control"] == "public, max-age=31536000, immutable"
    assert respuesta.content == bytes(variante.contenido)
    assert "Cookie" not in respuesta.get("Vary", "")


@pytest.mark.django_db
def test_el_nombre_de_un_rubro_se_muestra_escapado(client, negocio):
    Rubro.objects.create(nombre="<script>alert(1)</script>", orden=1)
    contenido = client.get("/").content.decode()
    assert "<script>alert(1)</script>" not in contenido
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in contenido


@pytest.mark.django_db
def test_los_rubros_del_inicio_no_suman_consultas_por_rubro(
    client, negocio, django_assert_max_num_queries
):
    _con_foto("Uno", orden=1)
    client.get("/")
    with CaptureQueriesContext(connection) as con_uno:
        client.get("/")
    for orden, nombre in enumerate(("Dos", "Tres", "Cuatro", "Cinco"), start=2):
        _con_foto(nombre, orden=orden)
    with django_assert_max_num_queries(len(con_uno.captured_queries)):
        client.get("/")


@pytest.mark.django_db
def test_solo_con_rubros_el_inicio_no_queda_en_preparacion(client):
    Rubro.objects.create(nombre="Industria", orden=1)
    contenido = client.get("/").content.decode()
    assert "Sitio en preparación" not in contenido and TITULO in contenido


@pytest.mark.django_db
def test_una_variante_es_de_una_imagen_o_de_un_rubro_nunca_de_ninguno():
    with pytest.raises(IntegrityError):
        VarianteImagen.objects.create(
            nombre="800", tipo_mime="image/webp", sha256="0" * 64, ancho=1, alto=1, contenido=b""
        )


# --- Rubros de partida -------------------------------------------------------------------


@pytest.mark.django_db
def test_cargar_rubros_crea_los_ocho_sin_foto_y_repetirlo_no_duplica():
    salida = io.StringIO()
    call_command("cargar_rubros", stdout=salida)
    assert "Se crearon 8 rubros" in salida.getvalue()
    assert list(Rubro.objects.values_list("nombre", "orden", "activo")) == [
        (nombre, orden, True) for orden, nombre in enumerate(rubros.INICIALES, start=1)
    ]
    assert not VarianteImagen.objects.exists()

    salida = io.StringIO()
    call_command("cargar_rubros", stdout=salida)
    assert "Ya hay rubros: no se cambió nada." in salida.getvalue()
    assert Rubro.objects.count() == 8


@pytest.mark.django_db
def test_cargar_rubros_no_revive_los_eliminados():
    call_command("cargar_rubros", stdout=io.StringIO())
    Rubro.objects.exclude(nombre="Construcción").delete()
    call_command("cargar_rubros", stdout=io.StringIO())
    assert list(Rubro.objects.values_list("nombre", flat=True)) == ["Construcción"]


def test_los_nombres_de_partida_caben_en_el_campo():
    largo = Rubro._meta.get_field("nombre").max_length
    assert all(len(nombre) <= largo for nombre in rubros.INICIALES)
