import json
import logging
import re
from unittest import mock

import pytest
from django.db import OperationalError
from django.test import Client

from core.logs import FormatoJson


@pytest.mark.django_db
def test_salud_responde_ok_consultando_la_base(client, django_assert_num_queries):
    with django_assert_num_queries(1):
        respuesta = client.get("/salud/")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok"}
    assert "no-store" in respuesta["Cache-Control"]


@pytest.mark.django_db
def test_salud_sin_base_de_datos_responde_503_sin_detalles(client):
    fallo = OperationalError("connection to server at 10.0.0.5 failed: clave incorrecta")
    with mock.patch("core.views.connection.cursor", side_effect=fallo):
        respuesta = client.get("/salud/")
    assert respuesta.status_code == 503
    assert respuesta.json() == {"estado": "error"}
    assert b"10.0.0.5" not in respuesta.content


@pytest.mark.django_db
def test_salud_solo_admite_get(client):
    assert client.post("/salud/").status_code == 405


@pytest.mark.django_db
def test_pagina_404_propia(client):
    respuesta = client.get("/esta-pagina-no-existe/")
    assert respuesta.status_code == 404
    contenido = respuesta.content.decode()
    assert "No encontramos esta página" in contenido
    assert 'lang="es-CL"' in contenido
    assert 'content="noindex"' in contenido


@pytest.mark.django_db
@pytest.mark.urls("core.tests.urls_prueba")
def test_pagina_500_propia_no_muestra_la_traza():
    cliente = Client(raise_request_exception=False)
    respuesta = cliente.get("/falla/")
    assert respuesta.status_code == 500
    contenido = respuesta.content.decode()
    assert "Ocurrió un problema en el servidor" in contenido
    assert "detalle interno" not in contenido
    assert "Traceback" not in contenido
    assert "RuntimeError" not in contenido


@pytest.mark.django_db
def test_la_referencia_de_componentes_no_existe_fuera_de_desarrollo(client):
    assert client.get("/_referencia/componentes/").status_code == 404


@pytest.mark.django_db
@pytest.mark.urls("core.tests.urls_prueba")
def test_la_referencia_muestra_los_componentes(client):
    respuesta = client.get("/_referencia/componentes/")
    assert respuesta.status_code == 200
    contenido = respuesta.content.decode()
    for marcador in (
        "boton-primario",
        "boton-secundario",
        "boton-fantasma",
        "boton-peligro",
        "boton-inverso",
        "boton-contorno-claro",
        "boton-ancho",
        "alerta-exito",
        "alerta-error",
        "insignia-error",
        "insignia-info",
        "insignia-exito",
        "insignia-neutro",
        "insignia-advertencia",
        'aria-label="Migas de pan"',
        'aria-label="Paginación"',
        'aria-label="Principal"',
        'aria-label="Pie de página"',
        'aria-label="Secciones"',
        'aria-label="Cuenta"',
        'aria-label="Pestañas de muestra"',
        'role="search"',
        "Titular de muestra de la portada",
        "Página 2 de 3",
        "12.345.678-5",
        # Tarjeta de empresa: el RUT se muestra con formato.
        "RUT: 76.111.111-6",
        # Filas de carpeta: plural, singular y sin fecha.
        "8 documentos · Actualizado el 15-01-2026",
        "1 documento · Actualizado el 15-01-2026",
        "0 documentos",
        # Fila de documento: tamaño legible y fecha chilena.
        "2,4\xa0MB · 15-01-2026",
        "lista-filas",
        'class="tabla"',
        'data-etiqueta="Estado"',
        "cuadro-icono-info",
        'data-copia="copiable-muestra"',
        'class="casilla"',
        'class="lateral-grupo"',
    ):
        assert marcador in contenido, marcador


@pytest.mark.django_db
@pytest.mark.urls("core.tests.urls_prueba")
def test_la_portada_no_lleva_imagen_mientras_no_haya_fotografias(client):
    contenido = client.get("/_referencia/componentes/").content.decode()
    assert "<img" not in contenido


@pytest.mark.django_db
@pytest.mark.urls("core.tests.urls_prueba")
def test_cada_tipo_de_archivo_tiene_su_icono_y_su_nombre_en_texto(client):
    contenido = client.get("/_referencia/componentes/").content.decode()
    for tipo, icono, nombre in (
        ("pdf", "lucide-file-text", "PDF"),
        ("word", "lucide-file-type", "Word"),
        ("excel", "lucide-file-spreadsheet", "Excel"),
        ("powerpoint", "lucide-presentation", "PowerPoint"),
        ("imagen", "lucide-file-image", "Imagen"),
    ):
        inicio = contenido.index(f'archivo-{tipo}"')
        bloque = contenido[inicio : inicio + 1500]
        assert icono in bloque, tipo
        assert f"{nombre}:" in bloque, tipo


@pytest.mark.django_db
@pytest.mark.urls("core.tests.urls_prueba")
def test_el_elemento_activo_de_la_navegacion_se_marca_con_aria_current(client):
    contenido = client.get("/_referencia/componentes/").content.decode()
    assert re.search(r'class="lateral-enlace" href="#" aria-current="page"', contenido)
    assert re.search(r'class="pestana" href="#" aria-current="page"', contenido)
    # Los elementos inactivos no llevan la marca.
    assert 'class="lateral-enlace" href="#">' in contenido
    assert 'class="pestana" href="#">' in contenido


@pytest.mark.django_db
@pytest.mark.urls("core.tests.urls_prueba")
def test_el_campo_de_contrasena_tiene_un_boton_accesible_para_mostrarla(client):
    contenido = client.get("/_referencia/componentes/").content.decode()
    assert '<input type="password" name="clave"' in contenido
    boton = re.search(r"<button[^>]*data-alterna-contrasena=\"id_clave\"[^>]*>", contenido)
    assert boton is not None
    for atributo in (
        'type="button"',
        'aria-controls="id_clave"',
        'aria-pressed="false"',
        'aria-label="Mostrar contraseña"',
    ):
        assert atributo in boton.group(0), atributo
    # Solo los campos de contraseña llevan el botón: uno por formulario de muestra.
    assert contenido.count("data-alterna-contrasena=") == 2


@pytest.mark.django_db
@pytest.mark.urls("core.tests.urls_prueba")
def test_los_id_de_la_pagina_no_se_repiten(client):
    """Un id repetido rompe las etiquetas, aria-describedby y el botón de la contraseña."""
    contenido = client.get("/_referencia/componentes/").content.decode()
    ids = re.findall(r'\sid="([^"]+)"', contenido)
    repetidos = {valor for valor in ids if ids.count(valor) > 1}
    assert not repetidos


@pytest.mark.django_db
@pytest.mark.urls("core.tests.urls_prueba")
def test_el_dialogo_de_confirmacion_es_nativo_y_envia_un_post_con_csrf(client):
    contenido = client.get("/_referencia/componentes/").content.decode()
    assert 'data-abre-dialogo="dialogo-muestra"' in contenido
    dialogo = re.search(
        r'<dialog class="dialogo" id="dialogo-muestra".*?</dialog>', contenido, re.S
    )
    assert dialogo is not None
    bloque = dialogo.group(0)
    assert 'aria-labelledby="dialogo-muestra-titulo"' in bloque
    assert 'aria-describedby="dialogo-muestra-mensaje"' in bloque
    # Cancelar cierra sin JavaScript; confirmar es un formulario POST con token.
    assert '<form method="dialog">' in bloque
    assert '<form method="post" action="/_referencia/componentes/">' in bloque
    assert 'name="csrfmiddlewaretoken"' in bloque


@pytest.mark.django_db
@pytest.mark.urls("core.tests.urls_prueba")
def test_confirmar_el_dialogo_redirige_y_muestra_el_mensaje_como_alerta():
    cliente = Client(enforce_csrf_checks=True)
    assert cliente.post("/_referencia/componentes/").status_code == 403

    pagina = cliente.get("/_referencia/componentes/")
    token = pagina.cookies["csrftoken"].value
    respuesta = cliente.post("/_referencia/componentes/", {"csrfmiddlewaretoken": token})
    assert respuesta.status_code == 302
    assert respuesta["Location"] == "/_referencia/componentes/"

    contenido = cliente.get("/_referencia/componentes/").content.decode()
    assert "Acción de muestra recibida" in contenido
    assert 'aria-live="polite"' in contenido
    # El mensaje se consume: no reaparece en la visita siguiente.
    assert (
        "Acción de muestra recibida"
        not in cliente.get("/_referencia/componentes/").content.decode()
    )


@pytest.mark.django_db
@pytest.mark.urls("core.tests.urls_prueba")
def test_el_campo_con_error_queda_asociado_a_su_mensaje(client):
    contenido = client.get("/_referencia/componentes/").content.decode()
    assert 'aria-invalid="true"' in contenido
    assert 'aria-describedby="conerror_rut_helptext conerror_rut_error"' in contenido
    assert 'id="conerror_rut_error"' in contenido
    assert "Ingrese un RUT válido" in contenido


@pytest.mark.django_db
@pytest.mark.urls("core.tests.urls_prueba")
def test_las_plantillas_no_llevan_estilos_ni_scripts_en_linea(client):
    """La CSP los bloquearía: se comprueba que ninguna plantilla base los use."""
    for ruta in ("/_referencia/componentes/", "/_referencia/404/", "/_referencia/500/"):
        contenido = client.get(ruta).content.decode()
        assert " style=" not in contenido, ruta
        assert "<style" not in contenido, ruta
        assert "<script>" not in contenido, ruta
        assert " onclick=" not in contenido, ruta


def test_formato_json_de_los_logs():
    registro = logging.LogRecord(
        "prueba", logging.WARNING, __file__, 1, "Mensaje ñ %s", ("x",), None
    )
    registro.status_code = 404
    salida = json.loads(FormatoJson().format(registro))
    assert salida["nivel"] == "WARNING"
    assert salida["origen"] == "prueba"
    assert salida["mensaje"] == "Mensaje ñ x"
    assert salida["codigo"] == 404
    assert "traza" not in salida


def test_los_logs_no_registran_el_token_de_los_enlaces():
    """El servidor anota la ruta de cada petición; el token del enlace no debe quedar ahí."""
    token = "_-zpdEsre_AM-K4WMebpxG2HmCtkobgRu00X8hYk5iU"
    for ruta in ("activar", "restablecer"):
        registro = logging.LogRecord(
            "django.server", logging.INFO, __file__, 1, '"%s %s HTTP/1.1" %s', None, None
        )
        registro.args = ("POST", f"/{ruta}/{token}/", 302)
        salida = json.loads(FormatoJson().format(registro))
        assert token not in salida["mensaje"]
        assert salida["mensaje"] == f'"POST /{ruta}/[oculto]/ HTTP/1.1" 302'

    try:
        raise RuntimeError(f"fallo en http://sitio.test/activar/{token}/?x=1")
    except RuntimeError:
        import sys

        registro = logging.LogRecord(
            "django.request", logging.ERROR, __file__, 1, "Error", None, sys.exc_info()
        )
    salida = json.loads(FormatoJson().format(registro))
    assert token not in salida["traza"] and "/activar/[oculto]" in salida["traza"]
    # Las demás rutas no se alteran.
    otro = logging.LogRecord("x", logging.INFO, __file__, 1, "GET /portal/ y /acceso/", None, None)
    assert json.loads(FormatoJson().format(otro))["mensaje"] == "GET /portal/ y /acceso/"
