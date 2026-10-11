import logging
import sys

import pytest
from django.core import mail
from django.core.management import CommandError, call_command

from core import avisos

TOKEN = "_-zpdEsre_AM-K4WMebpxG2HmCtkobgRu00X8hYk5iU"
CLAVE_ESCRITA = "caballo-bateria-grapa-2026"


@pytest.fixture(autouse=True)
def _cupo_limpio():
    avisos.reiniciar_cupo()
    yield
    avisos.reiniciar_cupo()


@pytest.fixture
def destinatarios(settings):
    settings.ERRORES_DESTINATARIOS = ["soporte@ejemplo.test"]
    return settings.ERRORES_DESTINATARIOS


def _registro_de_error(rf, ruta="/acceso/"):
    """Un registro como el que deja Django en `django.request` ante un error 500."""
    request = rf.post(ruta, {"rut": "11.111.111-1", "password": CLAVE_ESCRITA})
    try:
        raise RuntimeError(f"No se pudo guardar a juan@ejemplo.test con {CLAVE_ESCRITA}")
    except RuntimeError:
        registro = logging.LogRecord(
            "django.request",
            logging.ERROR,
            __file__,
            1,
            "Internal Server Error: %s",
            (ruta,),
            sys.exc_info(),
        )
    registro.request = request
    registro.status_code = 500
    return registro


def test_un_error_500_avisa_por_correo_al_administrador(rf, destinatarios):
    avisos.AvisoDeErrorPorCorreo().emit(_registro_de_error(rf))

    assert len(mail.outbox) == 1
    mensaje = mail.outbox[0]
    assert mensaje.to == destinatarios
    assert "Error 500" in mensaje.subject and "testserver" in mensaje.subject
    assert "POST /acceso/" in mensaje.body
    assert "RuntimeError" in mensaje.body
    # Dónde ocurrió: archivo, línea y función de cada marco.
    assert "test_avisos.py" in mensaje.body and "_registro_de_error" in mensaje.body


def test_el_aviso_no_lleva_datos_del_formulario_ni_el_mensaje_de_la_excepcion(rf, destinatarios):
    """SEG-10: el correo sale del servidor. El detalle completo queda solo en su log."""
    avisos.AvisoDeErrorPorCorreo().emit(_registro_de_error(rf))

    texto = mail.outbox[0].subject + mail.outbox[0].body
    assert CLAVE_ESCRITA not in texto
    assert "11.111.111-1" not in texto
    assert "juan@ejemplo.test" not in texto
    assert "csrf" not in texto.lower() and "cookie" not in texto.lower()


def test_el_aviso_oculta_el_token_de_los_enlaces(rf, destinatarios):
    avisos.AvisoDeErrorPorCorreo().emit(_registro_de_error(rf, f"/activar/{TOKEN}/"))

    texto = mail.outbox[0].subject + mail.outbox[0].body
    assert TOKEN not in texto
    assert "/activar/[oculto]/" in texto


def test_sin_destinatarios_no_se_envia_nada(rf, settings):
    settings.ERRORES_DESTINATARIOS = []
    avisos.AvisoDeErrorPorCorreo().emit(_registro_de_error(rf))
    assert mail.outbox == []


def test_los_avisos_tienen_un_tope_por_hora(rf, destinatarios, settings):
    """Un error que se repite en cada petición no agota el cupo diario del proveedor."""
    settings.ERRORES_AVISOS_POR_HORA = 3
    manejador = avisos.AvisoDeErrorPorCorreo()
    for _ in range(10):
        manejador.emit(_registro_de_error(rf))
    assert len(mail.outbox) == 3
    assert "no habrá más avisos" in mail.outbox[2].body
    assert "no habrá más avisos" not in mail.outbox[0].body


def test_el_cupo_se_recupera_al_pasar_la_hora(rf, destinatarios, settings, monkeypatch):
    settings.ERRORES_AVISOS_POR_HORA = 1
    manejador = avisos.AvisoDeErrorPorCorreo()
    reloj = [1000.0]
    monkeypatch.setattr(avisos.time, "monotonic", lambda: reloj[0])
    manejador.emit(_registro_de_error(rf))
    manejador.emit(_registro_de_error(rf))
    assert len(mail.outbox) == 1
    reloj[0] += 3601
    manejador.emit(_registro_de_error(rf))
    assert len(mail.outbox) == 2


def test_un_fallo_al_avisar_no_interrumpe_la_respuesta(rf, destinatarios, monkeypatch):
    def revienta(*args, **kwargs):
        raise OSError("sin red")

    monkeypatch.setattr("core.correo.enviar", revienta)
    # No debe propagar nada: el visitante ya está recibiendo la página de error.
    avisos.AvisoDeErrorPorCorreo().handle(_registro_de_error(rf))


@pytest.mark.django_db
@pytest.mark.urls("core.tests.urls_prueba")
def test_un_error_real_en_una_vista_llega_por_el_log_de_django(client, destinatarios):
    """El manejador está conectado a `django.request` en la configuración."""
    client.raise_request_exception = False
    assert client.get("/falla/").status_code == 500
    assert len(mail.outbox) == 1
    assert "GET /falla/" in mail.outbox[0].body
    assert "vista_que_falla" in mail.outbox[0].body
    assert "detalle interno" not in mail.outbox[0].body


def test_un_error_404_no_avisa(client, destinatarios, db):
    assert client.get("/no-existe/").status_code == 404
    assert mail.outbox == []


def test_avisar_fallo_envia_el_nombre_de_la_tarea(destinatarios, capsys):
    call_command("avisar_fallo", "respaldo")

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == destinatarios
    assert "respaldo" in mail.outbox[0].subject
    assert "journalctl" in mail.outbox[0].body
    assert "Aviso enviado" in capsys.readouterr().out


def test_avisar_fallo_dice_la_verdad_si_no_pudo_avisar(settings):
    """R4: el comando no termina bien si el correo no salió."""
    settings.ERRORES_DESTINATARIOS = []
    with pytest.raises(CommandError, match="ERRORES_DESTINATARIOS"):
        call_command("avisar_fallo", "respaldo")

    settings.ERRORES_DESTINATARIOS = ["soporte@ejemplo.test"]
    settings.DEFAULT_FROM_EMAIL = ""
    with pytest.raises(CommandError, match="no configurado"):
        call_command("avisar_fallo", "respaldo")
    assert mail.outbox == []


def test_avisar_fallo_rechaza_un_nombre_de_tarea_extrano(destinatarios):
    with pytest.raises(CommandError, match="nombre de la tarea"):
        call_command("avisar_fallo", "respaldo\nBcc: otro@ejemplo.test")
    assert mail.outbox == []
