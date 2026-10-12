"""Guardar y notificar (SOL-05, SOL-07, SOL-08, SOL-11) y prueba 13 de la sección 12.2."""

import datetime
import io
import runpy

import pytest
from django.core import mail
from django.core.management import call_command
from django.db import connection
from django.test import Client
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import Accion
from conftest import datos_de_consulta, datos_de_cotizacion
from solicitudes import services
from solicitudes.models import Solicitud

pytestmark = pytest.mark.django_db

CORREO_ROTO = {"default": {"BACKEND": "cuentas.tests.test_recuperacion.BackendQueFalla"}}
Notificacion = Solicitud.Notificacion


def _reintentar_notificaciones():
    salida = io.StringIO()
    call_command("reintentar_notificaciones", stdout=salida)
    return salida.getvalue()


def test_sol_08_el_correo_al_profesional_lleva_los_datos_el_enlace_y_el_reply_to(
    client, negocio, servicio
):
    client.post("/cotizacion/", datos_de_cotizacion())
    solicitud = Solicitud.objects.get()
    assert solicitud.notificacion == Notificacion.ENVIADA
    assert solicitud.notificada_en is not None and solicitud.notificacion_intentos == 1
    assert solicitud.notificacion_error == ""

    (correo,) = mail.outbox
    assert correo.subject == "Cotización de Visitante de Prueba"
    assert correo.to == ["profesional@ejemplo.test"]
    assert correo.reply_to == ["visitante@ejemplo.test"]
    assert correo.from_email == "pruebas@ejemplo.test"
    assert correo.attachments == [] and correo.cc == [] and correo.bcc == []
    for dato in (
        "Visitante de Prueba",
        "visitante@ejemplo.test",
        "+56 9 1234 5678",
        "Constructora de Prueba Ltda.",
        "Servicio de prueba",
        "11 a 25",
        "Talca",
        "Necesito información sobre sus servicios.",
        f"http://testserver/panel/solicitudes/{solicitud.pk}/",
    ):
        assert dato in correo.body, dato


def test_sol_07_el_visitante_no_recibe_ningun_correo(client, negocio):
    """El formulario no sirve para enviar correos a terceros."""
    client.post("/contacto/", datos_de_consulta(email="tercero@ejemplo.test"))
    (correo,) = mail.outbox
    assert correo.recipients() == ["profesional@ejemplo.test"]
    assert correo.subject == "Consulta de Visitante de Prueba"


def test_el_texto_del_correo_no_se_escapa_como_html(client, negocio):
    client.post("/contacto/", datos_de_consulta(mensaje="Seguridad & salud <en obra>"))
    assert "Seguridad & salud <en obra>" in mail.outbox[0].body


def test_prueba_13_con_el_correo_fallando_la_solicitud_se_guarda_y_el_panel_dice_fallida(
    negocio, servicio, settings, cliente_http_admin
):
    """El visitante ve la confirmación neutra de siempre; el fallo solo se ve en el panel."""
    settings.MAILERS = CORREO_ROTO
    visitante = Client()
    respuesta = visitante.post("/cotizacion/", datos_de_cotizacion())
    assert respuesta.status_code == 302 and respuesta["Location"] == "/solicitud-recibida/"

    confirmacion = visitante.get("/solicitud-recibida/").content.decode()
    assert "Recibimos su solicitud" in confirmacion
    assert "Le responderemos al correo o teléfono indicado." in confirmacion
    for texto in ("enviado", "enviamos", "notific", "error", "falló", "No pudimos"):
        assert texto not in confirmacion.split('id="contenido"')[1].split("<footer")[0], texto

    # La solicitud está completa, con el resultado real del envío.
    solicitud = Solicitud.objects.get()
    assert solicitud.nombre == "Visitante de Prueba" and solicitud.servicio == servicio
    assert solicitud.mensaje == "Necesito información sobre sus servicios."
    assert solicitud.notificacion == Notificacion.FALLIDA
    assert solicitud.notificacion_error and solicitud.notificacion_intentos == 1
    assert solicitud.notificada_en is None
    assert mail.outbox == []

    bandeja = cliente_http_admin.get("/panel/solicitudes/cotizaciones/").content.decode()
    assert "Visitante de Prueba" in bandeja and ">Fallida</span>" in bandeja
    detalle = cliente_http_admin.get(f"/panel/solicitudes/{solicitud.pk}/").content.decode()
    assert ">Fallida</span>" in detalle
    assert f"Error: {solicitud.notificacion_error}" in detalle
    assert "Reintentar notificación" in detalle
    assert (
        "Notificaciones por correo fallidas: 1"
        in cliente_http_admin.get("/panel/").content.decode()
    )

    # Con el correo todavía roto, el reintento lo dice y no afirma un envío.
    reintento = cliente_http_admin.post(
        f"/panel/solicitudes/{solicitud.pk}/reintentar/", follow=True
    ).content.decode()
    assert "La notificación volvió a fallar. La solicitud sigue guardada." in reintento
    assert "La notificación se envió" not in reintento
    solicitud.refresh_from_db()
    assert solicitud.notificacion == Notificacion.FALLIDA and solicitud.notificacion_intentos == 2

    # Reparado el correo, el reintento envía una sola notificación.
    settings.MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
    reintento = cliente_http_admin.post(
        f"/panel/solicitudes/{solicitud.pk}/reintentar/", follow=True
    ).content.decode()
    assert "La notificación se envió." in reintento and "Reintentar notificación" not in reintento
    solicitud.refresh_from_db()
    assert solicitud.notificacion == Notificacion.ENVIADA and solicitud.notificacion_error == ""
    assert solicitud.notificada_en is not None and solicitud.notificacion_intentos == 3
    (correo,) = mail.outbox
    assert correo.reply_to == ["visitante@ejemplo.test"]
    eventos = EventoAuditoria.objects.filter(accion=Accion.SOLICITUD_REINTENTO)
    assert [evento.detalle for evento in eventos.order_by("id")] == ["Fallida", "Enviada"]
    assert all(evento.objeto_uuid == solicitud.pk for evento in eventos)

    # Ya enviada, no se vuelve a enviar aunque se pida a mano.
    cliente_http_admin.post(f"/panel/solicitudes/{solicitud.pk}/reintentar/")
    assert len(mail.outbox) == 1


@pytest.mark.parametrize("sin", ["correo", "destinatarios", "remitente"])
def test_sol_05_sin_correo_configurado_la_solicitud_queda_como_no_configurada(
    client, negocio, settings, sin, cliente_http_admin
):
    if sin == "correo":
        settings.MAILERS = {}
    elif sin == "destinatarios":
        settings.NOTIFICACIONES_DESTINATARIOS = []
    else:
        settings.DEFAULT_FROM_EMAIL = ""
    respuesta = Client().post("/contacto/", datos_de_consulta())
    assert respuesta.status_code == 302 and respuesta["Location"] == "/solicitud-recibida/"

    solicitud = Solicitud.objects.get()
    assert solicitud.notificacion == Notificacion.NO_CONFIGURADA
    # No fue un intento fallido: no gasta los intentos del reintento automático.
    assert solicitud.notificacion_intentos == 0 and solicitud.notificada_en is None
    assert mail.outbox == []
    detalle = cliente_http_admin.get(f"/panel/solicitudes/{solicitud.pk}/").content.decode()
    assert ">Correo no configurado</span>" in detalle
    assert "La solicitud está guardada completa." in detalle


def test_el_orden_es_guardar_y_despues_notificar(negocio, monkeypatch):
    """SOL-05: cuando la notificación parte, la solicitud ya existe en la base."""
    vistas = []

    def notificar(solicitud_id):
        vistas.append(Solicitud.objects.filter(pk=solicitud_id).exists())

    monkeypatch.setattr(services, "notificar", notificar)
    Client().post("/contacto/", datos_de_consulta())
    assert vistas == [True]


def test_si_la_notificacion_revienta_la_solicitud_igual_queda_guardada(
    negocio, monkeypatch, settings
):
    """Ni un error inesperado al notificar pierde la solicitud o le llega al visitante: el
    trabajo ocurre fuera de la petición y queda "por enviar" para el reintento."""
    settings.TAREAS_SINCRONAS = False
    settings.TAREAS_ESPERA_SEGUNDOS = 0

    def notificar(solicitud_id):
        raise RuntimeError("fallo inesperado")

    monkeypatch.setattr(services, "notificar", notificar)
    monkeypatch.setattr("core.tareas.threading.Timer", _TemporizadorInmediato)
    # El hilo real cierra su propia conexión al terminar; aquí la tarea corre en el hilo
    # de la prueba, que debe conservar la suya.
    monkeypatch.setattr("core.tareas.connections.close_all", lambda: None)
    respuesta = Client().post("/contacto/", datos_de_consulta())
    assert respuesta.status_code == 302 and respuesta["Location"] == "/solicitud-recibida/"
    assert Solicitud.objects.get().notificacion == Notificacion.PENDIENTE


class _TemporizadorInmediato:
    """Ejecuta la tarea en el mismo hilo al iniciarla, sin esperar."""

    def __init__(self, espera, funcion, args=()):
        self.funcion, self.args = funcion, args

    def start(self):
        self.funcion(*self.args)


def _solicitud(**campos):
    datos = {
        "tipo": Solicitud.Tipo.CONSULTA,
        "nombre": "Visitante de Prueba",
        "email": "visitante@ejemplo.test",
        "mensaje": "Mensaje de prueba.",
        "consentimiento": True,
        "consentimiento_en": timezone.now(),
        **campos,
    }
    return Solicitud.objects.create(**datos)


def test_sol_11_reintentar_notificaciones_envia_las_fallidas_y_las_olvidadas(db, settings):
    hace_rato = timezone.now() - datetime.timedelta(minutes=30)
    fallida = _solicitud(notificacion=Notificacion.FALLIDA, notificacion_intentos=2)
    agotada = _solicitud(notificacion=Notificacion.FALLIDA, notificacion_intentos=5)
    olvidada = _solicitud()
    Solicitud.objects.filter(pk=olvidada.pk).update(creado_en=hace_rato)
    recien_llegada = _solicitud()
    sin_configurar = _solicitud(notificacion=Notificacion.NO_CONFIGURADA)
    enviada = _solicitud(notificacion=Notificacion.ENVIADA, notificacion_intentos=1)

    salida = _reintentar_notificaciones()
    assert "Enviadas: 3. Fallidas: 0." in salida and "Máximo de intentos por solicitud: 5" in salida
    assert len(mail.outbox) == 3
    estados = {
        nombre: Solicitud.objects.get(pk=solicitud.pk)
        for nombre, solicitud in {
            "fallida": fallida,
            "agotada": agotada,
            "olvidada": olvidada,
            "recien_llegada": recien_llegada,
            "sin_configurar": sin_configurar,
            "enviada": enviada,
        }.items()
    }
    assert estados["fallida"].notificacion == Notificacion.ENVIADA
    assert estados["fallida"].notificacion_intentos == 3
    assert estados["olvidada"].notificacion == Notificacion.ENVIADA
    assert estados["sin_configurar"].notificacion == Notificacion.ENVIADA
    # Sobre el máximo de intentos ya no se reintenta sola; la recién llegada es de su hilo.
    assert estados["agotada"].notificacion == Notificacion.FALLIDA
    assert estados["agotada"].notificacion_intentos == 5
    assert estados["recien_llegada"].notificacion == Notificacion.PENDIENTE
    assert estados["enviada"].notificacion_intentos == 1

    assert "No hay notificaciones por reintentar." in _reintentar_notificaciones()
    assert len(mail.outbox) == 3


def test_sol_11_la_consulta_liviana_cuenta_lo_mismo_que_la_tarea(db, settings, monkeypatch):
    """`docker/pendientes.py` decide si vale la pena cargar la aplicación: si contara de
    menos, una notificación fallida se quedaría sin reintentar."""
    guion = runpy.run_path(str(settings.BASE_DIR / "docker" / "pendientes.py"))

    def segun_el_guion():
        with connection.cursor() as cursor:
            cursor.execute(guion["CONSULTA"], {"maximo": guion["maximo_de_intentos"]()})
            return cursor.fetchone()[0]

    def segun_la_tarea():
        return Solicitud.objects.por_reintentar(
            maximo_intentos=settings.NOTIFICACIONES_INTENTOS_MAXIMOS,
            ahora=timezone.now(),
            correo_configurado=True,
        ).count()

    monkeypatch.delenv("NOTIFICACIONES_INTENTOS_MAXIMOS", raising=False)
    assert guion["SIN_PENDIENTES"] == 3
    assert segun_el_guion() == segun_la_tarea() == 0

    _solicitud(notificacion=Notificacion.ENVIADA, notificacion_intentos=1)
    _solicitud()  # recién llegada: todavía es de su hilo
    _solicitud(notificacion=Notificacion.FALLIDA, notificacion_intentos=5)  # agotada
    assert segun_el_guion() == segun_la_tarea() == 0

    _solicitud(notificacion=Notificacion.FALLIDA, notificacion_intentos=4)
    assert segun_el_guion() == segun_la_tarea() == 1
    olvidada = _solicitud()
    Solicitud.objects.filter(pk=olvidada.pk).update(
        creado_en=timezone.now() - datetime.timedelta(minutes=30)
    )
    _solicitud(notificacion=Notificacion.NO_CONFIGURADA)
    assert segun_el_guion() == segun_la_tarea() == 3

    # El máximo de intentos sale de la misma variable de entorno que usa la aplicación.
    monkeypatch.setenv("NOTIFICACIONES_INTENTOS_MAXIMOS", "2")
    settings.NOTIFICACIONES_INTENTOS_MAXIMOS = 2
    assert segun_el_guion() == segun_la_tarea() == 2


def test_sol_11_el_maximo_de_intentos_es_configurable_y_cada_fallo_cuenta(db, settings):
    settings.MAILERS = CORREO_ROTO
    settings.NOTIFICACIONES_INTENTOS_MAXIMOS = 2
    solicitud = _solicitud(notificacion=Notificacion.FALLIDA, notificacion_intentos=1)
    assert "Fallidas: 1." in _reintentar_notificaciones()
    solicitud.refresh_from_db()
    assert solicitud.notificacion_intentos == 2 and solicitud.notificacion == Notificacion.FALLIDA
    assert "No hay notificaciones por reintentar." in _reintentar_notificaciones()
    solicitud.refresh_from_db()
    assert solicitud.notificacion_intentos == 2


def test_sol_11_sin_correo_configurado_no_se_reintentan_las_no_configuradas(db, settings):
    settings.NOTIFICACIONES_DESTINATARIOS = []
    solicitud = _solicitud(notificacion=Notificacion.NO_CONFIGURADA)
    assert "No hay notificaciones por reintentar." in _reintentar_notificaciones()
    solicitud.refresh_from_db()
    assert solicitud.notificacion == Notificacion.NO_CONFIGURADA


def test_notificar_una_solicitud_ya_enviada_o_inexistente_no_hace_nada(db):
    import uuid

    enviada = _solicitud(notificacion=Notificacion.ENVIADA)
    assert services.notificar(enviada.pk) is None
    assert services.notificar(uuid.uuid4()) is None
    assert mail.outbox == []
