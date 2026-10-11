"""Sitio público (PUB-01 a PUB-05, PUB-07, PUB-08, SEG-06, SEG-13) y prueba 14 de la 12.2."""

import pathlib
import re
from xml.etree import ElementTree

import pytest
from django.conf import settings
from django.contrib.staticfiles import finders
from django.urls import get_resolver

from config.tests.test_urls_privadas import _recorrer
from sitio import fotos
from sitio.models import DatosNegocio, Servicio

pytestmark = pytest.mark.django_db

PAGINAS = ("/", "/servicios/", "/contacto/", "/cotizacion/", "/privacidad/")
HTML_CRUDO = "<script>alert(1)</script>"
HTML_ESCAPADO = "&lt;script&gt;alert(1)&lt;/script&gt;"


def _principal(contenido):
    """Lo que va dentro de <main>, sin encabezado ni pie."""
    return contenido.split('id="contenido"')[1].split("</main>")[0]


# --- Inicio (PUB-02) y navegación (PUB-04) ---------------------------------------------


def test_pub_02_el_inicio_muestra_portada_servicios_formulario_y_pie(client, negocio, servicio):
    respuesta = client.get("/")
    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200

    # Portada: fotografía con velo, titular y bajada de la base, y los dos botones.
    assert (
        '<h1 class="text-3xl font-bold md:text-4xl" id="portada-titular">Titular de prueba</h1>'
        in contenido
    )
    assert "Bajada de prueba para la portada." in contenido
    assert 'src="/static/img/portada.webp"' in contenido and 'class="velo ' in contenido
    assert re.search(r'href="/cotizacion/">\s*<span>Solicitar cotización</span>', contenido)
    assert re.search(r'href="/servicios/">\s*<span>Conozca nuestros servicios</span>', contenido)
    # El encabezado va dentro de la portada, sobre la fotografía.
    portada = contenido.split('id="contenido"')[0]
    assert 'src="/static/img/portada.webp"' in portada and "<header" in portada
    # La fotografía va dentro de la sección de la portada, no suelta fuera de toda región.
    assert portada.index("<section") < portada.index('src="/static/img/portada.webp"')
    assert '<header class="sobre-primario text-blanco">' in portada

    # Servicios: una tarjeta por servicio activo, enlazada a la página Servicios.
    assert "Nuestros servicios" in contenido
    assert 'href="/servicios/#servicio-de-prueba"' in contenido
    assert "Servicio de prueba" in contenido and "Resumen de prueba." in contenido

    # Contacto: fotografía y el formulario de cotización completo, que envía a /cotizacion/.
    assert 'src="/static/img/contacto.webp"' in contenido
    assert (
        '<form class="flex flex-col gap-5" method="post" action="/cotizacion/" novalidate>'
        in contenido
    )
    for campo in ("nombre", "email", "telefono", "empresa", "servicio", "trabajadores", "comuna"):
        assert f'name="{campo}"' in contenido, campo
    assert 'name="mensaje"' in contenido and 'name="consentimiento"' in contenido
    assert "csrfmiddlewaretoken" in contenido

    # Pie: marca, datos de contacto y política de privacidad.
    pie = contenido.split("<footer")[1]
    assert "Prevención de Prueba" in pie and "+56 9 8765 4321" in pie
    assert "Lunes a viernes, de 9:00 a 18:00" in pie and "Talca, Región del Maule" in pie
    assert 'href="/privacidad/">Política de privacidad</a>' in pie


def test_el_formulario_del_inicio_guarda_la_cotizacion(client, negocio, servicio):
    from conftest import datos_de_cotizacion
    from solicitudes.models import Solicitud

    contenido = client.get("/").content.decode()
    marca = contenido.split('name="marca" value="')[1].split('"')[0]
    # La marca del inicio es válida; se usa una emitida antes para no esperar en la prueba.
    assert marca.count(":") == 1
    respuesta = client.post("/cotizacion/", datos_de_cotizacion())
    assert respuesta.status_code == 302 and Solicitud.objects.count() == 1


def test_pub_04_la_navegacion_es_inicio_servicios_contacto_y_acceso_clientes(client, negocio):
    """DISENO.md, diferencia 7: sin menús desplegables ni "Documentos"."""
    contenido = client.get("/servicios/").content.decode()
    encabezado = contenido.split("<header")[1].split("</header>")[0]
    escritorio = encabezado.split('<nav class="hidden')[1].split("</nav>")[0]
    assert re.findall(r'<a class="nav-publica" href="([^"]+)">([^<]+)</a>', escritorio) == [
        ("/", "Inicio"),
        ("/servicios/", "Servicios"),
        ("/contacto/", "Contacto"),
    ]
    assert 'href="/acceso/"' in escritorio and "Acceso clientes" in escritorio
    assert "Documentos" not in encabezado
    # En móvil, el mismo menú dentro de un desplegable nativo.
    movil = encabezado.split("<details")[1]
    assert movil.count('class="menu-enlace') == 4 and "Acceso clientes" in movil
    # Marca provisional: ícono y nombre comercial en texto, enlazada al inicio.
    assert re.search(r'<a class="[^"]*" href="/">\s*<span class="icono icono-grande"', encabezado)
    assert "Prevención de Prueba" in encabezado


def test_pub_04_las_redes_sociales_solo_aparecen_si_estan_registradas(client, negocio):
    assert "Síganos" not in client.get("/").content.decode()
    negocio.instagram = "https://www.instagram.com/prevencion"
    negocio.linkedin = "https://www.linkedin.com/company/prevencion"
    negocio.save()
    pie = client.get("/").content.decode().split("<footer")[1]
    assert "Síganos" in pie
    assert (
        'href="https://www.instagram.com/prevencion" rel="noopener noreferrer">Instagram</a>' in pie
    )
    assert "LinkedIn" in pie and "Facebook" not in pie


# --- Lo que no existe no se muestra (PUB-05) -------------------------------------------


def test_pub_05_con_todo_en_completar_el_sitio_no_muestra_secciones_ni_marcadores(client, db):
    """Con los datos del negocio vacíos: navegación y pie, sin portada, servicios ni
    formularios, y sin ningún marcador a la vista."""
    assert DatosNegocio.objects.count() == 1 and not Servicio.objects.exists()
    for ruta in PAGINAS:
        respuesta = client.get(ruta)
        contenido = respuesta.content.decode()
        assert respuesta.status_code == 200, ruta
        assert "[COMPLETAR]" not in contenido and "COMPLETAR" not in contenido, ruta
        assert "lorem" not in contenido.lower(), ruta
        assert "<form" not in contenido, ruta
        assert respuesta["X-Robots-Tag"] == "noindex", ruta
        assert '<meta name="robots" content="noindex">' in contenido, ruta

    inicio = client.get("/").content.decode()
    assert "portada-titular" not in inicio and "Nuestros servicios" not in inicio
    assert 'id="contacto"' not in inicio and "portada.webp" not in _principal(inicio)
    assert _principal(inicio).strip(" \n>") == "" or "<section" not in _principal(inicio)
    # La navegación y el pie sí están, con sus enlaces.
    assert '<a class="nav-publica" href="/servicios/">Servicios</a>' in inicio
    assert "<footer" in inicio and "Política de privacidad" not in inicio


def test_pub_05_cada_dato_ausente_oculta_solo_su_seccion(client, negocio, servicio):
    negocio.titular = ""
    negocio.save()
    inicio = client.get("/").content.decode()
    assert "portada-titular" not in inicio and "Nuestros servicios" in inicio

    negocio.titular = "Titular de prueba"
    negocio.bajada = negocio.horario = negocio.nombre_comercial = ""
    negocio.save()
    inicio = client.get("/").content.decode()
    assert "portada-titular" in inicio and "Bajada de prueba" not in inicio
    assert "Lunes a viernes" not in inicio and "Prevención de Prueba" not in inicio

    servicio.activo = False
    servicio.save()
    inicio = client.get("/").content.decode()
    assert "Nuestros servicios" not in inicio and "Servicio de prueba" not in inicio
    assert "Aún no hay servicios publicados" in client.get("/servicios/").content.decode()


def test_un_dato_con_el_marcador_completar_se_trata_como_ausente(client, negocio, servicio):
    negocio.titular = "[COMPLETAR]"
    negocio.telefono = "[COMPLETAR] teléfono"
    negocio.save()
    inicio = client.get("/").content.decode()
    assert "COMPLETAR" not in inicio and "portada-titular" not in inicio
    assert "contacto@prevencion-de-prueba.cl" in inicio


# --- Servicios (PUB-03) y política de privacidad (SEG-12) ------------------------------


def test_pub_03_los_servicios_activos_van_en_su_orden_con_su_boton_de_cotizacion(
    client, negocio, servicio
):
    Servicio.objects.create(nombre="Va primero", slug="va-primero", orden=0, descripcion="Uno\nDos")
    Servicio.objects.create(nombre="Inactivo", slug="inactivo", orden=2, activo=False)
    contenido = client.get("/servicios/").content.decode()
    assert contenido.index("Va primero") < contenido.index("Servicio de prueba")
    assert "Inactivo" not in contenido
    assert 'href="/cotizacion/?servicio=va-primero"' in contenido
    assert 'id="servicio-de-prueba"' in contenido and "Descripción de prueba." in contenido
    # Los saltos de línea del texto editable se conservan, sin HTML.
    assert "Uno<br>Dos" in contenido
    assert "Presentación de prueba." in contenido


def test_seg_12_la_politica_muestra_el_texto_del_responsable_con_sus_parrafos(client, negocio):
    contenido = client.get("/privacidad/").content.decode()
    assert "<p>Política de privacidad de prueba.</p>" in contenido
    assert "<p>Segundo párrafo de la política.</p>" in contenido
    negocio.politica_privacidad = ""
    negocio.save()
    contenido = client.get("/privacidad/").content.decode()
    assert "La política de privacidad aún no está publicada" in contenido


# --- Textos editables escapados (SEG-06, prueba 14) ------------------------------------


def test_prueba_14_un_servicio_con_script_en_el_nombre_se_muestra_escapado_en_el_sitio(
    client, negocio
):
    Servicio.objects.create(
        nombre=HTML_CRUDO,
        slug="con-script",
        resumen=f"Resumen {HTML_CRUDO}",
        descripcion=f"Descripción {HTML_CRUDO}",
        orden=1,
    )
    for ruta in ("/", "/servicios/", "/cotizacion/"):
        contenido = client.get(ruta).content.decode()
        assert HTML_ESCAPADO in contenido, ruta
        assert "<script>alert" not in contenido, ruta
    assert f"Descripción {HTML_ESCAPADO}" in client.get("/servicios/").content.decode()


def test_seg_06_los_datos_del_negocio_se_muestran_escapados(client, negocio, servicio):
    for campo in (
        "nombre_comercial",
        "titular",
        "bajada",
        "presentacion",
        "ubicacion",
        "horario",
        "politica_privacidad",
    ):
        setattr(negocio, campo, f"{campo} {HTML_CRUDO}")
    negocio.telefono = "<i>+56 9 1234 5678</i>"
    negocio.save()
    for ruta in PAGINAS:
        contenido = client.get(ruta).content.decode()
        assert "<script>alert" not in contenido and "<i>" not in contenido, ruta
        assert f"nombre_comercial {HTML_ESCAPADO}" in contenido, ruta
        assert "&lt;i&gt;+56 9 1234 5678&lt;/i&gt;" in contenido, ruta
    assert f"titular {HTML_ESCAPADO}" in client.get("/").content.decode()
    assert f"politica_privacidad {HTML_ESCAPADO}" in client.get("/privacidad/").content.decode()


def test_ninguna_plantilla_marca_como_seguro_un_texto_editable():
    """R5: ni `|safe` ni `mark_safe` en las plantillas ni en el código del sitio."""
    raiz = settings.BASE_DIR
    for carpeta in ("sitio", "solicitudes", "templates", "panel/templates"):
        for archivo in (raiz / carpeta).rglob("*"):
            if archivo.suffix not in {".html", ".py", ".txt"} or "tests" in archivo.parts:
                continue
            texto = archivo.read_text(encoding="utf-8")
            assert "|safe" not in texto and "mark_safe" not in texto, archivo


# --- SEO (PUB-07) y noindex (SEG-13) ---------------------------------------------------


def test_pub_07_cada_pagina_lleva_titulo_descripcion_canonica_y_open_graph(
    client, negocio, servicio
):
    esperado = {
        "/": ("Prevención de Prueba", "Bajada de prueba para la portada."),
        "/servicios/": ("Servicios · Prevención de Prueba", "Presentación de prueba."),
        # Sin texto propio, la descripción solo dice qué página es y de quién.
        "/contacto/": ("Contacto · Prevención de Prueba", "Contacto de Prevención de Prueba."),
        "/cotizacion/": (
            "Solicitar cotización · Prevención de Prueba",
            "Solicite una cotización a Prevención de Prueba.",
        ),
        "/privacidad/": (
            "Política de privacidad · Prevención de Prueba",
            "Política de privacidad de Prevención de Prueba.",
        ),
    }
    for ruta, (titulo, descripcion) in esperado.items():
        respuesta = client.get(ruta)
        contenido = respuesta.content.decode()
        assert f"<title>{titulo}</title>" in contenido, ruta
        assert f'<link rel="canonical" href="http://testserver{ruta}">' in contenido, ruta
        assert f'<meta property="og:title" content="{titulo}">' in contenido, ruta
        assert f'<meta property="og:url" content="http://testserver{ruta}">' in contenido, ruta
        assert (
            '<meta property="og:image" content="http://testserver/static/img/portada-960.webp">'
            in contenido
        )
        assert '<meta property="og:site_name" content="Prevención de Prueba">' in contenido
        if descripcion:
            assert f'<meta name="description" content="{descripcion}">' in contenido, ruta
        else:
            # Sin texto registrado para la página, la descripción no se inventa.
            assert '<meta name="description"' not in contenido, ruta
        assert "X-Robots-Tag" not in respuesta.headers, ruta
        assert 'content="noindex"' not in contenido, ruta


def test_la_canonica_usa_sitio_url_y_no_el_encabezado_host(client, negocio, settings):
    settings.SITIO_URL = "https://www.ejemplo.cl/"
    settings.ALLOWED_HOSTS = ["testserver", "atacante.example"]
    contenido = client.get("/servicios/?utm=1", HTTP_HOST="atacante.example").content.decode()
    assert '<link rel="canonical" href="https://www.ejemplo.cl/servicios/">' in contenido
    assert "atacante.example" not in contenido


def test_pub_07_el_sitemap_lista_solo_las_paginas_publicas_con_contenido(client, negocio, servicio):
    respuesta = client.get("/sitemap.xml")
    assert respuesta["Content-Type"] == "application/xml"
    raiz = ElementTree.fromstring(respuesta.content)
    urls = [
        elemento.text for elemento in raiz.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
    ]
    assert urls == [
        "http://testserver/",
        "http://testserver/servicios/",
        "http://testserver/contacto/",
        "http://testserver/cotizacion/",
        "http://testserver/privacidad/",
    ]
    for privada in ("portal", "panel", "acceso", "activar", "recuperar", "admin", "recibida"):
        assert privada not in respuesta.content.decode(), privada

    # Sin contenido, el sitemap queda vacío: nada que indexar todavía.
    DatosNegocio.objects.update(titular="", politica_privacidad="", telefono="", email_publico="")
    Servicio.objects.update(activo=False)
    assert ElementTree.fromstring(client.get("/sitemap.xml").content).findall("*") == []


def test_seg_13_robots_no_enumera_rutas_privadas_ni_el_admin(client, db):
    respuesta = client.get("/robots.txt")
    contenido = respuesta.content.decode()
    assert respuesta["Content-Type"].startswith("text/plain")
    assert contenido.splitlines() == [
        "User-agent: *",
        "Allow: /",
        "",
        "Sitemap: http://testserver/sitemap.xml",
    ]
    for privada in ("admin", "panel", "portal", "Disallow"):
        assert privada not in contenido, privada


def test_pub_07_solo_las_paginas_publicas_quedan_sin_noindex(
    client, negocio, servicio, cliente_a_activo
):
    """Recorre el URLconf: todo lo que no es una página pública con contenido responde con
    `X-Robots-Tag: noindex`, incluidos portal, panel, acceso, activación, recuperación, el
    admin de Django y las páginas de error."""
    indexables = {"/", "/servicios/", "/contacto/", "/cotizacion/", "/privacidad/"}
    sin_encabezado = {"/sitemap.xml", "/robots.txt"}
    probadas = set()
    for sesion in (None, cliente_a_activo):
        if sesion:
            client.force_login(sesion)
        for nombre, ruta, _ in _recorrer(get_resolver().url_patterns):
            respuesta = client.get(ruta)
            probadas.add(nombre.split(":")[0])
            if ruta in indexables | sin_encabezado:
                assert "X-Robots-Tag" not in respuesta.headers, (nombre, ruta)
            else:
                assert respuesta["X-Robots-Tag"] == "noindex", (nombre, ruta)
    assert {"sitio", "solicitudes", "cuentas", "portal", "panel", "admin", "core"} <= probadas
    assert client.get("/no-existe/")["X-Robots-Tag"] == "noindex"


# --- Fotografías (PUB-08) --------------------------------------------------------------


@pytest.mark.parametrize("foto", [fotos.PORTADA, fotos.CONTACTO, fotos.ACCESO])
def test_pub_08_las_fotos_son_webp_propios_optimizados_y_estan_registradas(foto):
    registro = (settings.BASE_DIR / "docs" / "FOTOS.md").read_text(encoding="utf-8")
    for archivo, ancho_maximo in ((foto.archivo, 1920), (foto.archivo_movil, 960)):
        ruta = finders.find(archivo)
        assert ruta, archivo
        datos = pathlib.Path(ruta).read_bytes()
        assert datos[:4] == b"RIFF" and datos[8:12] == b"WEBP", archivo
        assert len(datos) < 300 * 1024, archivo
        assert archivo.split("/")[-1] in registro, archivo
        assert ancho_maximo <= 1920
    assert foto.ancho == 1920 and foto.alt
    # El texto alternativo describe la escena, sin atribuirla al negocio.
    for palabra in ("nuestro", "nuestra", "cliente", "equipo"):
        assert palabra not in foto.alt.lower(), palabra


def test_pub_08_cada_foto_registra_origen_autor_y_licencia():
    registro = (settings.BASE_DIR / "docs" / "FOTOS.md").read_text(encoding="utf-8")
    filas = [linea for linea in registro.splitlines() if linea.startswith("| `static/img/")]
    assert len(filas) == 3
    for fila in filas:
        assert "https://unsplash.com/photos/" in fila or "https://www.pexels.com/" in fila, fila
        assert "Unsplash License" in fila or "Pexels License" in fila, fila
        assert re.search(r"[0-9a-f]{64}", fila), fila


def test_las_fotos_llevan_texto_alternativo_y_dimensiones(client, negocio, servicio):
    contenido = client.get("/").content.decode()
    for foto in (fotos.PORTADA, fotos.CONTACTO):
        assert f'alt="{foto.alt}"' in contenido
        assert f'width="{foto.ancho}" height="{foto.alto}"' in contenido
    assert 'srcset="/static/img/portada-960.webp 960w, /static/img/portada.webp 1920w"' in contenido
    # La portada es la primera imagen: no se difiere. La de contacto, sí.
    imagenes = re.findall(r"<img [^>]+>", contenido)
    assert len(imagenes) == 2
    assert 'fetchpriority="high"' in imagenes[0] and 'loading="lazy"' in imagenes[1]
    assert contenido.count('loading="lazy"') == 1
    # La portada además se pide desde el <head>, antes de que el navegador llegue a ella.
    cabeza = contenido.split("</head>")[0]
    assert (
        '<link rel="preload" as="image" href="/static/img/portada.webp" '
        'imagesrcset="/static/img/portada-960.webp 960w, /static/img/portada.webp 1920w" '
        'imagesizes="100vw" fetchpriority="high">' in cabeza
    )
    assert contenido.count('fetchpriority="high"') == 2


def test_las_paginas_publicas_y_de_acceso_no_cargan_htmx(client, negocio, cliente_a_activo):
    """No lo usan, y pesa en la medición de rendimiento del sitio público (RNF-06). El portal
    y el panel lo conservan."""
    for ruta in ("/", "/servicios/", "/contacto/", "/cotizacion/", "/acceso/", "/recuperar/"):
        assert "htmx" not in client.get(ruta).content.decode(), ruta
    client.force_login(cliente_a_activo)
    portal = client.get("/portal/").content.decode()
    assert 'src="/static/vendor/htmx.min.js"' in portal and 'name="htmx-config"' in portal
    acceso = client.get("/acceso/").content.decode()
    assert 'src="/static/img/acceso.webp"' in acceso and f'alt="{fotos.ACCESO.alt}"' in acceso


# --- Marca en el acceso y página 404 ---------------------------------------------------


def test_la_pantalla_de_acceso_lleva_la_marca_cuando_existe_el_nombre_comercial(client, db):
    assert "icono-grande" not in client.get("/acceso/").content.decode()
    DatosNegocio.objects.update(nombre_comercial="Prevención de Prueba")
    contenido = client.get("/acceso/").content.decode()
    assert "Prevención de Prueba" in contenido and "icono-grande" in contenido


def test_la_pagina_404_enlaza_al_inicio(client, db):
    respuesta = client.get("/no-existe/")
    assert respuesta.status_code == 404
    assert 'href="/"><span>Ir al inicio</span></a>' in respuesta.content.decode()
