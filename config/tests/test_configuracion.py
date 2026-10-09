import datetime
import os
import subprocess
import sys

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import formats, translation

from config import env

CLAVE_VALIDA = "x9" * 30
ENTORNO_VALIDO = {
    "SECRET_KEY": CLAVE_VALIDA,
    "ALLOWED_HOSTS": "ejemplo.cl",
    "DATABASE_URL": "postgres://usuario:clave@db.ejemplo.cl:5432/base",
    "PROXY_CONFIANZA_REDES": "10.0.0.0/8",
    "SITIO_URL": "https://ejemplo.cl",
}


def _importar_prod(entorno, codigo="import config.settings.prod"):
    """Importa config.settings.prod en un proceso nuevo, solo con el entorno indicado."""
    base = {
        nombre: os.environ[nombre]
        for nombre in ("PATH", "SYSTEMROOT", "PYTHONPATH")
        if nombre in os.environ
    }
    return subprocess.run(
        [sys.executable, "-c", codigo],
        env={**base, **entorno},
        cwd=settings.BASE_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_prod_arranca_con_la_configuracion_minima():
    resultado = _importar_prod(ENTORNO_VALIDO)
    assert resultado.returncode == 0, resultado.stderr


@pytest.mark.parametrize("variable", ["SECRET_KEY", "ALLOWED_HOSTS", "DATABASE_URL"])
def test_prod_se_niega_a_arrancar_si_falta_una_variable(variable):
    entorno = {nombre: valor for nombre, valor in ENTORNO_VALIDO.items() if nombre != variable}
    resultado = _importar_prod(entorno)
    assert resultado.returncode != 0
    assert "ImproperlyConfigured" in resultado.stderr
    assert variable in resultado.stderr


@pytest.mark.parametrize("variable", ["SECRET_KEY", "ALLOWED_HOSTS", "DATABASE_URL"])
def test_prod_trata_una_variable_vacia_como_faltante(variable):
    resultado = _importar_prod({**ENTORNO_VALIDO, variable: "  "})
    assert resultado.returncode != 0
    assert variable in resultado.stderr


def test_prod_exige_declarar_los_proxies_de_confianza_aunque_sea_vacio():
    sin_variable = {k: v for k, v in ENTORNO_VALIDO.items() if k != "PROXY_CONFIANZA_REDES"}
    resultado = _importar_prod(sin_variable)
    assert resultado.returncode != 0
    assert "PROXY_CONFIANZA_REDES" in resultado.stderr
    assert _importar_prod({**ENTORNO_VALIDO, "PROXY_CONFIANZA_REDES": ""}).returncode == 0


def test_prod_exige_la_url_del_sitio_con_https():
    sin_variable = {k: v for k, v in ENTORNO_VALIDO.items() if k != "SITIO_URL"}
    for entorno in (sin_variable, {**ENTORNO_VALIDO, "SITIO_URL": "http://ejemplo.cl"}):
        resultado = _importar_prod(entorno)
        assert resultado.returncode != 0
        assert "SITIO_URL" in resultado.stderr


def test_prod_rechaza_una_red_de_proxy_invalida():
    resultado = _importar_prod({**ENTORNO_VALIDO, "PROXY_CONFIANZA_REDES": "cualquiera"})
    assert resultado.returncode != 0
    assert "PROXY_CONFIANZA_REDES" in resultado.stderr


def test_prod_se_niega_a_arrancar_con_la_clave_de_ejemplo():
    resultado = _importar_prod({**ENTORNO_VALIDO, "SECRET_KEY": env.CLAVE_DE_EJEMPLO})
    assert resultado.returncode != 0
    assert "valor de ejemplo" in resultado.stderr


def test_la_clave_de_ejemplo_es_la_de_env_example():
    """Si alguien cambia .env.example, la comprobación de producción debe seguirle."""
    contenido = (settings.BASE_DIR / ".env.example").read_text(encoding="utf-8")
    assert f"SECRET_KEY={env.CLAVE_DE_EJEMPLO}\n" in contenido


def test_prod_rechaza_claves_cortas_y_el_comodin_de_hosts():
    assert _importar_prod({**ENTORNO_VALIDO, "SECRET_KEY": "corta"}).returncode != 0
    assert _importar_prod({**ENTORNO_VALIDO, "ALLOWED_HOSTS": "*"}).returncode != 0


def test_prod_no_muestra_la_url_de_la_base_si_es_invalida():
    resultado = _importar_prod({**ENTORNO_VALIDO, "DATABASE_URL": "mysql://u:secreto123@host/base"})
    assert resultado.returncode != 0
    assert "secreto123" not in resultado.stderr


def test_idioma_y_zona_horaria():
    assert settings.LANGUAGE_CODE == "es-cl"
    assert settings.TIME_ZONE == "America/Santiago"
    assert settings.USE_TZ is True


def test_fechas_con_formato_chileno_y_textos_en_espanol():
    assert formats.date_format(datetime.date(2026, 10, 9)) == "09-10-2026"
    assert formats.date_format(datetime.datetime(2026, 10, 9, 8, 5), "DATETIME_FORMAT") == (
        "09-10-2026 08:05"
    )
    assert translation.gettext("This field is required.") == "Este campo es obligatorio."


def test_contrasenas_con_argon2_y_minimo_de_12_caracteres():
    assert settings.PASSWORD_HASHERS[0] == "django.contrib.auth.hashers.Argon2PasswordHasher"
    minimo = next(
        validador["OPTIONS"]["min_length"]
        for validador in settings.AUTH_PASSWORD_VALIDATORS
        if validador["NAME"].endswith("MinimumLengthValidator")
    )
    assert minimo == 12


@pytest.mark.django_db
def test_encabezados_de_seguridad(client):
    respuesta = client.get("/esta-pagina-no-existe/")
    csp = respuesta["Content-Security-Policy"]
    assert "default-src 'none'" in csp
    assert "script-src 'self'" in csp
    assert "style-src 'self'" in csp
    assert "unsafe-inline" not in csp
    assert respuesta["X-Frame-Options"] == "DENY"
    assert respuesta["X-Content-Type-Options"] == "nosniff"
    assert respuesta["Referrer-Policy"] == "same-origin"


def test_env_booleano_entero_y_lista(monkeypatch):
    monkeypatch.setenv("PRUEBA_BOOLEANO", "Sí")
    monkeypatch.setenv("PRUEBA_ENTERO", "42")
    monkeypatch.setenv("PRUEBA_LISTA", " a, b ,,c ")
    assert env.booleano("PRUEBA_BOOLEANO") is True
    assert env.booleano("PRUEBA_AUSENTE", defecto=True) is True
    assert env.entero("PRUEBA_ENTERO", 1) == 42
    assert env.entero("PRUEBA_AUSENTE", 7) == 7
    assert env.lista("PRUEBA_LISTA") == ["a", "b", "c"]
    assert env.lista("PRUEBA_AUSENTE", ["x"]) == ["x"]

    monkeypatch.setenv("PRUEBA_BOOLEANO", "quizás")
    monkeypatch.setenv("PRUEBA_ENTERO", "doce")
    with pytest.raises(ImproperlyConfigured):
        env.booleano("PRUEBA_BOOLEANO")
    with pytest.raises(ImproperlyConfigured):
        env.entero("PRUEBA_ENTERO", 1)


def test_env_base_de_datos(monkeypatch):
    monkeypatch.setenv("PRUEBA_URL", "postgres://usuario:cl%40ve@servidor:5433/mi_base")
    assert env.base_de_datos("PRUEBA_URL") == {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "mi_base",
        "USER": "usuario",
        "PASSWORD": "cl@ve",
        "HOST": "servidor",
        "PORT": "5433",
    }
