import datetime
import io
import json
import logging
import runpy
from types import SimpleNamespace

import pytest
from django.conf import settings
from gunicorn.config import Config
from gunicorn.glogging import Logger

TOKEN = "_-zpdEsre_AM-K4WMebpxG2HmCtkobgRu00X8hYk5iU"
_REGISTRADORES = ("", "gunicorn.error", "gunicorn.access")


@pytest.fixture
def configuracion():
    return runpy.run_path(str(settings.BASE_DIR / "config" / "gunicorn.py"))


@pytest.fixture
def registro_de_gunicorn(configuracion):
    """El registrador de Gunicorn con la configuración de producción, y lo que escribe.
    Al terminar, los registradores vuelven a como los dejó Django."""
    antes = {
        nombre: (
            logging.getLogger(nombre).handlers[:],
            logging.getLogger(nombre).level,
            logging.getLogger(nombre).propagate,
        )
        for nombre in _REGISTRADORES
    }
    cfg = Config()
    for clave in ("accesslog", "access_log_format", "logconfig_dict"):
        cfg.set(clave, configuracion[clave])
    try:
        registro = Logger(cfg)
        # El manejador de la configuración escribe en stdout; aquí, en memoria.
        (manejador,) = logging.getLogger("gunicorn.access").handlers
        assert logging.getLogger("gunicorn.error").handlers == [manejador]
        salida = io.StringIO()
        manejador.setStream(salida)
        yield registro, salida
    finally:
        for nombre, (manejadores, nivel, propaga) in antes.items():
            registrador = logging.getLogger(nombre)
            registrador.handlers[:] = manejadores
            registrador.setLevel(nivel)
            registrador.propagate = propaga


def _peticion(registro, ruta, consulta=""):
    respuesta = SimpleNamespace(status="302 Found", sent=0, headers=[])
    peticion = SimpleNamespace(headers=[], method="POST", path=ruta, query=consulta)
    entorno = {
        "REMOTE_ADDR": "172.30.57.2",
        "REQUEST_METHOD": "POST",
        "PATH_INFO": ruta,
        "QUERY_STRING": consulta,
        "RAW_URI": ruta + (f"?{consulta}" if consulta else ""),
        "SERVER_PROTOCOL": "HTTP/1.1",
    }
    registro.access(respuesta, peticion, entorno, datetime.timedelta(milliseconds=12))


def test_gunicorn_escucha_en_tcp_y_no_en_un_socket_unix(configuracion):
    """Sin una IP en la conexión, todos los clientes compartirían los límites por IP."""
    assert configuracion["bind"] == "0.0.0.0:8000"
    assert not configuracion["bind"].startswith("unix:")
    assert configuracion["worker_class"] == "gthread"


def test_el_log_de_acceso_de_gunicorn_no_registra_el_token_de_los_enlaces(
    registro_de_gunicorn,
):
    """SEG-10: Gunicorn anota la ruta de cada petición, también la de los enlaces."""
    registro, salida = registro_de_gunicorn
    for ruta in ("activar", "restablecer"):
        _peticion(registro, f"/{ruta}/{TOKEN}/")
        linea = salida.getvalue().splitlines()[-1]
        assert TOKEN not in linea
        entrada = json.loads(linea)
        assert entrada["origen"] == "gunicorn.access"
        assert entrada["mensaje"].startswith(f"POST /{ruta}/[oculto]/ 302 ")


def test_el_log_de_acceso_no_lleva_la_consulta_ni_la_ip(registro_de_gunicorn):
    """La cadena de consulta trae lo que la persona buscó; la IP queda solo en la auditoría."""
    registro, salida = registro_de_gunicorn
    _peticion(registro, "/portal/buscar/", "q=licencia+medica+de+juan")
    linea = salida.getvalue()
    assert "juan" not in linea and "172.30.57.2" not in linea
    assert json.loads(linea)["mensaje"].startswith("POST /portal/buscar/ 302 ")


def test_los_errores_de_gunicorn_tambien_salen_en_json(registro_de_gunicorn):
    registro, salida = registro_de_gunicorn
    registro.error("Fallo en /activar/%s/", TOKEN)
    entrada = json.loads(salida.getvalue())
    assert entrada["nivel"] == "ERROR" and entrada["origen"] == "gunicorn.error"
    assert entrada["mensaje"] == "Fallo en /activar/[oculto]/"


def test_gunicorn_carga_la_aplicacion_una_vez_y_usa_un_proceso_de_cuatro_hilos(
    configuracion, monkeypatch
):
    """DEC-189: la aplicación se carga antes de crear los procesos. DEC-194: un proceso de
    cuatro hilos, que ocupa menos memoria que dos de dos; se puede cambiar por entorno."""
    assert configuracion["preload_app"] is True
    assert (configuracion["workers"], configuracion["threads"]) == (1, 4)

    monkeypatch.setenv("GUNICORN_PROCESOS", "2")
    monkeypatch.setenv("GUNICORN_HILOS", "2")
    otra = runpy.run_path(str(settings.BASE_DIR / "config" / "gunicorn.py"))
    assert (otra["workers"], otra["threads"]) == (2, 2)


def test_el_log_de_acceso_no_lleva_la_url_firmada_de_una_descarga(registro_de_gunicorn):
    """SEG-10: la descarga responde con una redirección a una URL firmada. Gunicorn anota
    la ruta pedida, nunca los encabezados de la respuesta."""
    registro, salida = registro_de_gunicorn
    firmada = "https://storage.googleapis.com/b/docs/e/v?X-Amz-Signature=0123abcd&X-Amz-Expires=120"
    ruta = "/portal/documentos/47ccd7fb-8af1-42c0-8196-68629b793b60/descargar/"
    respuesta = SimpleNamespace(status="302 Found", sent=0, headers=[("Location", firmada)])
    peticion = SimpleNamespace(headers=[], method="GET", path=ruta, query="")
    entorno = {
        "REMOTE_ADDR": "172.30.57.2",
        "REQUEST_METHOD": "GET",
        "PATH_INFO": ruta,
        "QUERY_STRING": "",
        "RAW_URI": ruta,
        "SERVER_PROTOCOL": "HTTP/1.1",
    }
    registro.access(respuesta, peticion, entorno, datetime.timedelta(milliseconds=12))
    linea = salida.getvalue()
    assert "X-Amz" not in linea and "0123abcd" not in linea and "googleapis" not in linea
    assert json.loads(linea)["mensaje"].startswith(f"GET {ruta} 302 ")
