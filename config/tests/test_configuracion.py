import datetime
import os
import re
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
    "PROXY_HTTPS_ENCABEZADO": "X-Forwarded-Proto",
    "SITIO_URL": "https://ejemplo.cl",
    "DOCUMENTOS_ALMACENAMIENTO": "local",
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
    # Vacía es válida: sin proxy, tampoco se lee su encabezado de HTTPS.
    directo = {**ENTORNO_VALIDO, "PROXY_CONFIANZA_REDES": "", "PROXY_HTTPS_ENCABEZADO": ""}
    assert _importar_prod(directo).returncode == 0


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


@pytest.mark.django_db
@pytest.mark.parametrize("ruta", ["/esta-pagina-no-existe/", "/acceso/", "/salud/", "/portal/"])
def test_todas_las_respuestas_llevan_una_permissions_policy_restrictiva(client, ruta):
    politica = client.get(ruta)["Permissions-Policy"]
    for funcion in ("camera", "microphone", "geolocation", "payment", "usb", "display-capture"):
        assert f"{funcion}=()" in politica, funcion
    # Ninguna función queda delegada, ni al propio origen.
    assert "self" not in politica and "*" not in politica


@pytest.mark.django_db
def test_sin_una_ip_valida_en_la_conexion_queda_un_error_en_el_log(client, caplog):
    """Tras un socket Unix no hay REMOTE_ADDR: todos compartirían los mismos contadores."""
    with caplog.at_level("ERROR", logger="core.middleware"):
        assert client.get("/salud/", REMOTE_ADDR="").status_code == 200
    assert "No se pudo determinar la IP del cliente" in caplog.text


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


def test_env_example_documenta_todas_las_variables_que_lee_la_configuracion():
    """Sección 13: cada variable de entorno queda documentada en .env.example."""
    import re

    leidas = set()
    for archivo in (settings.BASE_DIR / "config" / "settings").glob("*.py"):
        codigo = archivo.read_text(encoding="utf-8")
        leidas |= set(re.findall(r'env\.\w+\(\s*"([A-Z0-9_]+)"', codigo))
        leidas |= set(re.findall(r'"([A-Z0-9_]+)" not in os\.environ', codigo))
    # La define la imagen Docker, no quien despliega.
    leidas.discard("ESTATICOS_COMPILADOS_DIR")
    assert {"SECRET_KEY", "SITIO_URL", "PROXY_CONFIANZA_REDES", "CORREO_HOST"} <= leidas

    ejemplo = (settings.BASE_DIR / ".env.example").read_text(encoding="utf-8")
    documentadas = set(re.findall(r"^([A-Z0-9_]+)=", ejemplo, flags=re.M))
    assert leidas <= documentadas, sorted(leidas - documentadas)


def test_prod_exige_declarar_el_almacenamiento_de_documentos():
    sin_variable = {k: v for k, v in ENTORNO_VALIDO.items() if k != "DOCUMENTOS_ALMACENAMIENTO"}
    resultado = _importar_prod(sin_variable)
    assert resultado.returncode != 0
    assert "DOCUMENTOS_ALMACENAMIENTO" in resultado.stderr


_VER_HTTPS = (
    "import config.settings.prod as p; "
    "print(getattr(p, 'SECURE_PROXY_SSL_HEADER', None), p.CSRF_TRUSTED_ORIGINS, "
    "p.SECURE_HSTS_INCLUDE_SUBDOMAINS, p.SECURE_HSTS_PRELOAD)"
)


def test_prod_reconoce_https_detras_del_proxy_declarado():
    """Sin esto, con el proxy terminando TLS, la redirección a HTTPS no termina nunca."""
    resultado = _importar_prod(ENTORNO_VALIDO, _VER_HTTPS)
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip() == (
        "('HTTP_X_FORWARDED_PROTO', 'https') ['https://ejemplo.cl'] False False"
    )


def test_prod_exige_el_encabezado_de_https_si_hay_proxy_y_no_lo_lee_si_no_lo_hay():
    sin_encabezado = {k: v for k, v in ENTORNO_VALIDO.items() if k != "PROXY_HTTPS_ENCABEZADO"}
    resultado = _importar_prod(sin_encabezado)
    assert resultado.returncode != 0 and "PROXY_HTTPS_ENCABEZADO" in resultado.stderr

    directo = {**sin_encabezado, "PROXY_CONFIANZA_REDES": ""}
    resultado = _importar_prod(directo, _VER_HTTPS)
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.startswith("None ")

    # Sin proxy de confianza, cualquiera podría enviar el encabezado.
    resultado = _importar_prod({**directo, "PROXY_HTTPS_ENCABEZADO": "X-Forwarded-Proto"})
    assert resultado.returncode != 0 and "PROXY_HTTPS_ENCABEZADO" in resultado.stderr


def test_prod_admite_origenes_csrf_y_hsts_ampliado_por_variables():
    entorno = {
        **ENTORNO_VALIDO,
        "CSRF_TRUSTED_ORIGINS": "https://ejemplo.cl,https://www.ejemplo.cl",
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": "true",
        "SECURE_HSTS_PRELOAD": "true",
    }
    resultado = _importar_prod(entorno, _VER_HTTPS)
    assert resultado.stdout.strip().endswith(
        "['https://ejemplo.cl', 'https://www.ejemplo.cl'] True True"
    )


_CHECK_DEPLOY = (
    "import os, django; os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.prod'; "
    "django.setup(); from django.core.management import call_command; "
    "call_command('check', deploy=True, fail_level='WARNING')"
)


def test_check_deploy_con_la_configuracion_de_produccion():
    """SEG-01. Las dos únicas advertencias admitidas están justificadas en SEGURIDAD.md: HSTS
    para subdominios y `preload` se activan por variable al confirmar el dominio."""

    def advertencias(entorno):
        resultado = _importar_prod(entorno, _CHECK_DEPLOY)
        assert "SystemCheckError" in resultado.stderr, resultado.stderr
        return set(re.findall(r"[(](\w+[.][WE]\d+)[)]", resultado.stdout + resultado.stderr))

    # Una clave como la que se genera para producción, y el servidor de correo configurado.
    produccion = {
        **ENTORNO_VALIDO,
        "SECRET_KEY": "k7#Qm2xLw9!Tz4pVb6@Hn8rYc1$Fd3sGj5%Ae0uXo7&Ni2Rt-Wq8Zs",
        "CORREO_HOST": "smtp.ejemplo.cl",
        "CORREO_REMITENTE": "no-responder@ejemplo.cl",
    }
    assert advertencias(produccion) == {"security.W005", "security.W021"}

    completo = {
        **produccion,
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": "true",
        "SECURE_HSTS_PRELOAD": "true",
    }
    resultado = _importar_prod(completo, _CHECK_DEPLOY)
    assert resultado.returncode == 0, resultado.stderr
    assert "no issues" in resultado.stdout

    # Sin servidor de correo la aplicación arranca, y Django lo advierte: los envíos quedan
    # registrados como "correo no configurado".
    sin_correo = {k: v for k, v in completo.items() if not k.startswith("CORREO_")}
    assert advertencias(sin_correo) == {"mail.W001"}
