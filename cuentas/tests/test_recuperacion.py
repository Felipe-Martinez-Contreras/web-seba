"""Recuperación de contraseña sin revelar si la cuenta existe (AUT-07; prueba 7 de 12.2)."""

import re
import threading
from unittest import mock

import pytest
from django.core import mail
from django.db import connection
from django.test.utils import CaptureQueriesContext

from auditoria.models import EventoAuditoria
from auditoria.services import Accion
from conftest import RUT_ADMINISTRADOR, RUT_CLIENTE_A, RUT_CLIENTE_B, RUT_INEXISTENTE
from core import correo, tareas
from cuentas import services
from cuentas.models import EnlaceAcceso

pytestmark = pytest.mark.django_db

TEXTO_FIJO = (
    "Si los datos corresponden a una cuenta activa, enviaremos instrucciones al correo registrado."
)


def _pedir(client, rut, **extra):
    return client.post("/recuperar/", {"rut": rut}, **extra)


def _enlace_del_correo(mensaje):
    return re.search(r"http://\S+/restablecer/\S+/", mensaje.body).group(0)


def test_la_respuesta_es_identica_para_un_rut_existente_y_uno_inexistente(client, cliente_a_activo):
    respuestas = {}
    for rut in (RUT_CLIENTE_A, RUT_INEXISTENTE):
        respuesta = _pedir(client, rut)
        assert respuesta.status_code == 302
        pagina = client.get(respuesta["Location"])
        # El token CSRF de la página cambia en cada respuesta por diseño.
        cuerpo = re.sub(r'"X-CSRFToken": "[^"]+"', "", pagina.content.decode())
        respuestas[rut] = (respuesta["Location"], pagina.status_code, cuerpo)
    assert respuestas[RUT_CLIENTE_A] == respuestas[RUT_INEXISTENTE]
    ubicacion, codigo, contenido = respuestas[RUT_CLIENTE_A]
    assert ubicacion == "/recuperar/enviado/" and codigo == 200
    texto = contenido
    assert TEXTO_FIJO in texto
    # No afirma ningún envío.
    assert "Enviamos" not in texto and "Hemos enviado" not in texto
    assert 'content="noindex"' in texto


def test_solo_la_cuenta_activa_con_correo_recibe_el_enlace_y_el_enlace_funciona(
    client, cliente_a_activo
):
    _pedir(client, RUT_CLIENTE_A)
    assert len(mail.outbox) == 1
    mensaje = mail.outbox[0]
    assert mensaje.to == ["cliente.a@ejemplo.test"]
    assert mensaje.subject == "Restablecer su contraseña"
    assert mensaje.from_email == "pruebas@ejemplo.test"
    assert "60 minutos" in mensaje.body and "una sola vez" in mensaje.body
    assert not mensaje.attachments

    url = _enlace_del_correo(mensaje)
    assert url.startswith("http://testserver/restablecer/")
    respuesta = client.post(
        url,
        {
            "new_password1": "tornillo-violeta-marea-88",
            "new_password2": "tornillo-violeta-marea-88",
        },
    )
    assert respuesta.status_code == 302 and respuesta["Location"] == "/portal/"

    enlace = EnlaceAcceso.objects.get()
    assert enlace.tipo == EnlaceAcceso.Tipo.RESTABLECIMIENTO
    assert enlace.envio == EnlaceAcceso.Envio.ENVIADA and enlace.usado_en is not None
    envio = EventoAuditoria.objects.get(accion=Accion.RECUPERACION_CORREO)
    assert envio.detalle == "Enviada" and envio.objeto_uuid == cliente_a_activo.uuid


def test_no_se_envia_nada_a_cuentas_que_no_califican(
    client, cliente_a_activo, cliente_b_activo, administrador, empresa_b
):
    cliente_a_activo.is_active = False
    cliente_a_activo.save()
    empresa_b.activa = False
    empresa_b.save()
    cliente_b_activo.email = "cliente.b@ejemplo.test"
    cliente_b_activo.save()
    administrador.email = ""
    administrador.save()

    for rut in (RUT_CLIENTE_A, RUT_CLIENTE_B, RUT_ADMINISTRADOR, RUT_INEXISTENTE):
        respuesta = _pedir(client, rut)
        assert respuesta["Location"] == "/recuperar/enviado/"
    assert mail.outbox == []
    assert not EnlaceAcceso.objects.exists()
    # Las cuatro solicitudes quedan en la auditoría, con el RUT intentado.
    assert EventoAuditoria.objects.filter(accion=Accion.RECUPERACION_SOLICITADA).count() == 4


def test_una_cuenta_sin_activar_puede_recuperar(client, administrador):
    """Tiene correo y está activa: el enlace le sirve para definir su primera contraseña."""
    _pedir(client, RUT_ADMINISTRADOR)
    assert [m.to for m in mail.outbox] == [["admin@ejemplo.test"]]


def test_un_rut_con_digito_incorrecto_muestra_error_de_formato(client):
    respuesta = _pedir(client, "11.111.111-2")
    assert respuesta.status_code == 200
    assert "Ingrese un RUT válido" in respuesta.content.decode()
    assert not EventoAuditoria.objects.exists()


def test_el_enlace_usa_la_url_configurada_y_no_el_encabezado_host(
    client, cliente_a_activo, settings
):
    settings.ALLOWED_HOSTS = ["testserver", "malicioso.example"]
    settings.SITIO_URL = "https://portal.ejemplo.cl/"
    _pedir(client, RUT_CLIENTE_A, HTTP_HOST="malicioso.example")
    cuerpo = mail.outbox[0].body
    assert "https://portal.ejemplo.cl/restablecer/" in cuerpo
    assert "malicioso" not in cuerpo


def test_el_envio_ocurre_fuera_de_la_peticion(client, cliente_a_activo):
    """La petición solo entrega la tarea: no crea el enlace ni habla con el servidor de correo."""
    llamadas = []
    with mock.patch.object(tareas, "en_segundo_plano", side_effect=lambda *a: llamadas.append(a)):
        for rut in (RUT_CLIENTE_A, RUT_INEXISTENTE):
            assert _pedir(client, rut)["Location"] == "/recuperar/enviado/"
    assert mail.outbox == []
    assert not EnlaceAcceso.objects.exists()
    # Se entrega siempre, exista o no la cuenta; solo cambia el argumento.
    assert [llamada[0] for llamada in llamadas] == [services.enviar_enlace_de_recuperacion] * 2
    assert [llamada[1] for llamada in llamadas] == [cliente_a_activo.pk, None]


def test_la_peticion_hace_las_mismas_consultas_exista_o_no_la_cuenta(client, cliente_a_activo):
    consultas = []
    with mock.patch.object(tareas, "en_segundo_plano"):
        for rut in (RUT_CLIENTE_A, RUT_INEXISTENTE, RUT_CLIENTE_A, RUT_INEXISTENTE):
            with CaptureQueriesContext(connection) as contexto:
                _pedir(client, rut)
            consultas.append(len(contexto))
    assert len(set(consultas)) == 1, consultas


def test_limite_silencioso_por_rut(client, cliente_a_activo, settings):
    settings.RECUPERACION_MAXIMO_POR_RUT = 3
    respuestas = [_pedir(client, RUT_CLIENTE_A) for _ in range(5)]
    assert {r["Location"] for r in respuestas} == {"/recuperar/enviado/"}
    assert len(mail.outbox) == 3
    sobre_el_limite = EventoAuditoria.objects.filter(
        accion=Accion.RECUPERACION_SOLICITADA, detalle="Sobre el límite de solicitudes"
    )
    # Superar el límite deja un solo evento, no uno por cada petición siguiente.
    assert sobre_el_limite.count() == 1


def test_limite_silencioso_por_ip(client, cliente_a_activo, settings):
    settings.RECUPERACION_MAXIMO_POR_IP = 2
    for rut in ("1-9", "2-7"):
        _pedir(client, rut)
    assert _pedir(client, RUT_CLIENTE_A)["Location"] == "/recuperar/enviado/"
    assert mail.outbox == []


def test_sin_correo_configurado_queda_registrado_y_la_pantalla_no_cambia(
    client, cliente_a_activo, settings
):
    settings.MAILERS = {}
    respuesta = _pedir(client, RUT_CLIENTE_A)
    assert respuesta["Location"] == "/recuperar/enviado/"
    assert EnlaceAcceso.objects.get().envio == EnlaceAcceso.Envio.NO_CONFIGURADA
    evento = EventoAuditoria.objects.get(accion=Accion.RECUPERACION_CORREO)
    assert evento.detalle == "Correo no configurado"


def test_si_el_servidor_de_correo_falla_queda_registrado_y_la_pantalla_no_cambia(
    client, cliente_a_activo, settings, caplog
):
    settings.MAILERS = {"default": {"BACKEND": "cuentas.tests.test_recuperacion.BackendQueFalla"}}
    respuesta = _pedir(client, RUT_CLIENTE_A)
    assert respuesta["Location"] == "/recuperar/enviado/"
    assert TEXTO_FIJO in client.get("/recuperar/enviado/").content.decode()

    enlace = EnlaceAcceso.objects.get()
    assert enlace.envio == EnlaceAcceso.Envio.FALLIDA
    assert enlace.envio_error == "ConnectionRefusedError"
    assert EventoAuditoria.objects.get(accion=Accion.RECUPERACION_CORREO).detalle == "Fallida"
    assert "Correo de recuperación no enviado" in caplog.text
    # Ni el enlace ni el token llegan al log.
    assert "/restablecer/" not in caplog.text


class BackendQueFalla:
    def __init__(self, **opciones):
        pass

    def send_messages(self, mensajes):
        raise ConnectionRefusedError("servidor de correo inalcanzable")


def test_un_enlace_cuyo_envio_no_termino_queda_como_pendiente(cliente_a_activo):
    """Si el proceso se reinicia en medio del envío, el registro no dice "enviada"."""

    def proceso_interrumpido(*args, **kwargs):
        raise SystemExit

    with (
        mock.patch.object(correo, "enviar", side_effect=proceso_interrumpido),
        pytest.raises(SystemExit),
    ):
        services.enviar_enlace_de_recuperacion(cliente_a_activo.pk, "203.0.113.7")
    assert EnlaceAcceso.objects.get().envio == EnlaceAcceso.Envio.PENDIENTE
    assert not EventoAuditoria.objects.filter(accion=Accion.RECUPERACION_CORREO).exists()


def test_la_tarea_no_hace_nada_si_la_cuenta_dejo_de_calificar(cliente_a_activo):
    services.enviar_enlace_de_recuperacion(None, "203.0.113.7")
    cliente_a_activo.is_active = False
    cliente_a_activo.save()
    services.enviar_enlace_de_recuperacion(cliente_a_activo.pk, "203.0.113.7")
    services.enviar_enlace_de_recuperacion(999_999, "203.0.113.7")
    assert mail.outbox == [] and not EnlaceAcceso.objects.exists()


# --- core.tareas: el hilo de envío -------------------------------------------------------


def test_en_las_pruebas_la_tarea_se_ejecuta_en_el_mismo_hilo(settings):
    assert settings.TAREAS_SINCRONAS is True
    hilos = []
    assert tareas.en_segundo_plano(lambda: hilos.append(threading.current_thread())) is None
    assert hilos == [threading.current_thread()]


def test_fuera_de_las_pruebas_la_tarea_corre_en_otro_hilo_y_cierra_su_conexion(settings):
    settings.TAREAS_SINCRONAS = False
    settings.TAREAS_ESPERA_SEGUNDOS = 0.2
    hilos = []
    with mock.patch.object(tareas.connections, "close_all") as cerrar:
        hilo = tareas.en_segundo_plano(
            lambda valor: hilos.append((valor, threading.current_thread())), 7
        )
        # No parte de inmediato: quien la lanza termina primero su respuesta.
        assert hilos == []
        hilo.join(timeout=10)
    assert not hilo.is_alive()
    assert hilos[0][0] == 7 and hilos[0][1] is not threading.current_thread()
    cerrar.assert_called_once_with()


def test_la_espera_antes_de_trabajar_tiene_una_parte_al_azar(settings):
    settings.TAREAS_SINCRONAS = False
    settings.TAREAS_ESPERA_SEGUNDOS = 30
    hilos = [tareas.en_segundo_plano(print) for _ in range(5)]
    esperas = {hilo.interval for hilo in hilos}
    for hilo in hilos:
        hilo.cancel()
    assert all(30 <= espera <= 60 for espera in esperas)
    assert len(esperas) > 1


def test_un_error_en_el_hilo_se_registra_y_la_conexion_se_cierra_igual(settings, caplog):
    settings.TAREAS_SINCRONAS = False

    def tarea_que_falla():
        raise RuntimeError("fallo de prueba")

    settings.TAREAS_ESPERA_SEGUNDOS = 0
    with mock.patch.object(tareas.connections, "close_all") as cerrar:
        tareas.en_segundo_plano(tarea_que_falla).join(timeout=10)
    cerrar.assert_called_once_with()
    assert "Falló una tarea en segundo plano: tarea_que_falla" in caplog.text


def _entradas_por_rut():
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM cache WHERE cache_key LIKE %s", ["%recuperar:rut:%"])
        return cursor.fetchone()[0]


def test_sobre_el_limite_por_ip_no_se_crean_entradas_por_rut_ni_un_evento_por_peticion(
    client, settings
):
    """Quien supera su límite no puede seguir llenando la caché ni la auditoría."""
    settings.RECUPERACION_MAXIMO_POR_IP = 2
    ruts = ("11.111.111-1", "22.222.222-2", "12.345.678-5", "9.876.543-3", "5.126.663-3")
    for rut in ruts:
        assert _pedir(client, rut)["Location"] == "/recuperar/enviado/"
    assert _entradas_por_rut() == 2
    eventos = EventoAuditoria.objects.filter(accion=Accion.RECUPERACION_SOLICITADA)
    # Las dos dentro del límite y una sola que deja constancia de que se superó.
    assert eventos.count() == 3
    assert eventos.filter(detalle="Sobre el límite de solicitudes").count() == 1


def test_la_recuperacion_no_revoca_el_enlace_de_activacion_vigente(client, cliente_a):
    """Con solo conocer el RUT, cualquiera podía inutilizar el enlace que entregó el
    administrador."""
    cliente_a.email = "cliente.a@ejemplo.test"
    cliente_a.save()
    _, activacion = services.generar_enlace(cliente_a, EnlaceAcceso.Tipo.ACTIVACION)

    _pedir(client, RUT_CLIENTE_A)
    primero = _enlace_del_correo(mail.outbox[0])
    assert services.enlace_vigente(EnlaceAcceso.Tipo.ACTIVACION, activacion) is not None

    # Un restablecimiento nuevo sí reemplaza al restablecimiento anterior.
    _pedir(client, RUT_CLIENTE_A)
    assert client.get(primero.removeprefix("http://testserver")).status_code == 404
    assert services.enlace_vigente(EnlaceAcceso.Tipo.ACTIVACION, activacion) is not None

    # Al usar uno, los demás dejan de valer.
    segundo = _enlace_del_correo(mail.outbox[1]).removeprefix("http://testserver")
    nueva = "otra-clave-larga-2026"
    client.post(segundo, {"new_password1": nueva, "new_password2": nueva})
    assert services.enlace_vigente(EnlaceAcceso.Tipo.ACTIVACION, activacion) is None
