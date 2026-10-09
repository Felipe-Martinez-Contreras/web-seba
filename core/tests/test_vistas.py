import json
import logging
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
    for clase in (
        "boton-primario",
        "boton-secundario",
        "boton-fantasma",
        "boton-peligro",
        "alerta-exito",
        "alerta-error",
        "insignia-advertencia",
        'aria-label="Migas de pan"',
        'aria-label="Paginación"',
        'aria-label="Panel"',
        "Página 2 de 3",
        "12.345.678-5",
    ):
        assert clase in contenido, clase
    # El mensaje de Django se muestra como alerta de éxito.
    assert "Así se ve la confirmación" in contenido


@pytest.mark.django_db
@pytest.mark.urls("core.tests.urls_prueba")
def test_el_campo_con_error_queda_asociado_a_su_mensaje(client):
    contenido = client.get("/_referencia/componentes/").content.decode()
    assert 'aria-invalid="true"' in contenido
    assert 'aria-describedby="id_rut_helptext id_rut_error"' in contenido
    assert 'id="id_rut_error"' in contenido
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
