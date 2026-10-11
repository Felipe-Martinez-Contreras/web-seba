"""Formularios públicos de consulta y cotización (SOL-01 a SOL-03, SOL-06, SEG-12; E1)."""

import pytest
from django.core import mail
from django.test import Client

from auditoria.models import EventoAuditoria
from conftest import datos_de_consulta, datos_de_cotizacion
from sitio.models import Servicio
from solicitudes.models import Solicitud

pytestmark = pytest.mark.django_db

CONFIRMACION = "Recibimos su solicitud"


def test_sol_01_la_consulta_se_guarda_y_lleva_a_la_confirmacion(client, negocio):
    respuesta = client.post("/contacto/", datos_de_consulta())
    assert respuesta.status_code == 302 and respuesta["Location"] == "/solicitud-recibida/"

    solicitud = Solicitud.objects.get()
    assert solicitud.tipo == Solicitud.Tipo.CONSULTA
    assert solicitud.nombre == "Visitante de Prueba"
    assert solicitud.email == "visitante@ejemplo.test"
    assert solicitud.mensaje == "Necesito información sobre sus servicios."
    assert solicitud.estado == Solicitud.Estado.PENDIENTE
    assert solicitud.consentimiento is True and solicitud.consentimiento_en is not None
    assert solicitud.servicio is None and solicitud.servicio_texto == ""
    # Recibir una solicitud no deja evento de auditoría: guardaría la IP del visitante.
    assert not EventoAuditoria.objects.exists()

    contenido = client.get("/solicitud-recibida/").content.decode()
    assert CONFIRMACION in contenido
    assert "Le responderemos al correo o teléfono indicado." in contenido


def test_sol_06_la_confirmacion_solo_se_muestra_a_quien_acaba_de_enviar(client, negocio):
    """R4: la página afirma que se recibió una solicitud; sin envío, lleva al inicio."""
    respuesta = client.get("/solicitud-recibida/")
    assert respuesta.status_code == 302 and respuesta["Location"] == "/"

    client.post("/contacto/", datos_de_consulta())
    assert CONFIRMACION in client.get("/solicitud-recibida/").content.decode()
    # Recargar la confirmación no la vuelve a mostrar ni crea otra solicitud.
    assert client.get("/solicitud-recibida/").status_code == 302
    assert Solicitud.objects.count() == 1


def test_sol_02_la_cotizacion_guarda_todos_sus_datos(client, negocio, servicio):
    respuesta = client.post("/cotizacion/", datos_de_cotizacion())
    assert respuesta.status_code == 302
    solicitud = Solicitud.objects.get()
    assert solicitud.tipo == Solicitud.Tipo.COTIZACION
    assert solicitud.telefono == "+56 9 1234 5678"
    assert solicitud.empresa == "Constructora de Prueba Ltda."
    assert solicitud.servicio == servicio
    assert solicitud.trabajadores == Solicitud.Trabajadores.HASTA_25
    assert solicitud.comuna == "Talca"


def test_sol_02_otro_o_no_estoy_seguro_no_exige_un_servicio(client, negocio, servicio):
    client.post("/cotizacion/", datos_de_cotizacion(servicio="otro"))
    solicitud = Solicitud.objects.get()
    assert solicitud.servicio is None
    assert solicitud.servicio_texto == "Otro / no estoy seguro"


def test_sol_02_el_selector_ofrece_solo_los_servicios_activos(client, negocio, servicio):
    Servicio.objects.create(nombre="Servicio retirado", slug="retirado", orden=2, activo=False)
    contenido = client.get("/cotizacion/").content.decode()
    assert '<option value="servicio-de-prueba">Servicio de prueba</option>' in contenido
    assert '<option value="otro">Otro / no estoy seguro</option>' in contenido
    assert "Servicio retirado" not in contenido
    # Un servicio inactivo tampoco se acepta con una petición hecha a mano.
    respuesta = client.post("/cotizacion/", datos_de_cotizacion(servicio="retirado"))
    assert respuesta.status_code == 200 and not Solicitud.objects.exists()


def test_e1_la_cotizacion_desde_un_servicio_llega_preseleccionada_hasta_la_bandeja(
    client, negocio, servicio, cliente_http_admin
):
    """E1: del botón del servicio a la bandeja del panel, con su estado de notificación."""
    visitante = Client()
    servicios = visitante.get("/servicios/").content.decode()
    assert 'href="/cotizacion/?servicio=servicio-de-prueba"' in servicios

    formulario = visitante.get("/cotizacion/?servicio=servicio-de-prueba").content.decode()
    assert '<option value="servicio-de-prueba" selected>Servicio de prueba</option>' in formulario
    # Un identificador desconocido no preselecciona nada ni rompe la página.
    otro = visitante.get("/cotizacion/?servicio=no-existe").content.decode()
    assert " selected>Servicio de prueba" not in otro

    respuesta = visitante.post("/cotizacion/", datos_de_cotizacion(), follow=True)
    assert CONFIRMACION in respuesta.content.decode()

    bandeja = cliente_http_admin.get("/panel/solicitudes/cotizaciones/").content.decode()
    assert "Visitante de Prueba" in bandeja and "Servicio de prueba" in bandeja
    assert ">Pendiente</span>" in bandeja and ">Enviada</span>" in bandeja
    assert len(mail.outbox) == 1


@pytest.mark.parametrize(
    ("ruta", "cambios", "error"),
    [
        ("/contacto/", {"nombre": ""}, "Este campo es obligatorio."),
        ("/contacto/", {"email": "no-es-un-correo"}, "correo electrónico válida"),
        ("/contacto/", {"mensaje": ""}, "Este campo es obligatorio."),
        ("/contacto/", {"mensaje": "x" * 2001}, "2000 caracteres"),
        ("/contacto/", {"consentimiento": ""}, "Debe aceptar la política de privacidad"),
        ("/contacto/", {"telefono": "llámeme"}, "Ingrese un teléfono válido"),
        ("/contacto/", {"nombre": "Ana\r\nBcc: otro@ejemplo.test"}, "saltos de línea"),
        ("/cotizacion/", {"telefono": ""}, "Este campo es obligatorio."),
        ("/cotizacion/", {"servicio": ""}, "Este campo es obligatorio."),
        ("/cotizacion/", {"servicio": "inventado"}, "Escoja una opción válida"),
        ("/cotizacion/", {"trabajadores": "muchos"}, "Escoja una opción válida"),
        ("/cotizacion/", {"empresa": "Uno\nDos"}, "saltos de línea"),
    ],
)
def test_sol_03_el_servidor_valida_cada_campo_y_conserva_lo_escrito(
    client, negocio, servicio, ruta, cambios, error
):
    datos = datos_de_cotizacion() if ruta == "/cotizacion/" else datos_de_consulta()
    respuesta = client.post(ruta, {**datos, **cambios})
    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert error in contenido
    assert "Revise los campos marcados e intente nuevamente." in contenido
    assert 'aria-live="assertive"' in contenido and 'aria-invalid="true"' in contenido
    # Lo que sí estaba bien escrito sigue en el formulario.
    assert 'value="visitante@ejemplo.test"' in contenido or "email" in cambios
    assert not Solicitud.objects.exists() and mail.outbox == []


def test_sol_03_los_campos_opcionales_lo_dicen_y_el_telefono_depende_del_formulario(
    client, negocio, servicio
):
    consulta = client.get("/contacto/").content.decode()
    assert 'name="telefono"' in consulta and 'name="empresa"' not in consulta
    cotizacion = client.get("/cotizacion/").content.decode()
    for campo in ("empresa", "servicio", "trabajadores", "comuna", "mensaje", "consentimiento"):
        assert f'name="{campo}"' in cotizacion, campo
    assert 'name="telefono"' in cotizacion and 'id="id_telefono" required' not in consulta
    assert 'maxlength="2000"' in cotizacion


def test_seg_12_sin_politica_de_privacidad_no_hay_formularios(client, negocio, servicio):
    """Sin el texto de la política no se muestran ni se aceptan los formularios; en su lugar
    va el contacto registrado."""
    negocio.politica_privacidad = ""
    negocio.save()
    for ruta in ("/", "/contacto/", "/cotizacion/"):
        contenido = client.get(ruta).content.decode()
        assert "<form" not in contenido, ruta
        assert "Solicitar cotización</span>" not in contenido, ruta
        assert 'href="tel:+56987654321"' in contenido, ruta
        assert 'href="mailto:contacto@prevencion-de-prueba.cl"' in contenido, ruta
    assert "Solicitar cotización" not in client.get("/servicios/").content.decode()

    for ruta, datos in (
        ("/contacto/", datos_de_consulta()),
        ("/cotizacion/", datos_de_cotizacion()),
    ):
        assert client.post(ruta, datos).status_code == 404
    assert not Solicitud.objects.exists()


def test_sin_politica_y_sin_contacto_la_pagina_explica_que_el_formulario_no_esta(client, db):
    for ruta in ("/contacto/", "/cotizacion/"):
        respuesta = client.get(ruta)
        contenido = respuesta.content.decode()
        assert respuesta.status_code == 200
        assert "El formulario no está disponible por ahora" in contenido
        assert "<form" not in contenido and "[COMPLETAR]" not in contenido
        assert respuesta["X-Robots-Tag"] == "noindex"


def test_el_formulario_enlaza_la_politica_y_registra_la_fecha_de_aceptacion(client, negocio):
    contenido = client.get("/contacto/").content.decode()
    assert 'href="/privacidad/" target="_blank" rel="noopener"' in contenido
    assert "Acepto la política de privacidad" in contenido
    client.post("/contacto/", datos_de_consulta())
    solicitud = Solicitud.objects.get()
    assert abs((solicitud.consentimiento_en - solicitud.creado_en).total_seconds()) < 5


def test_la_base_rechaza_una_solicitud_sin_consentimiento(db):
    from django.db import IntegrityError, transaction
    from django.utils import timezone

    with pytest.raises(IntegrityError), transaction.atomic():
        Solicitud.objects.create(
            tipo=Solicitud.Tipo.CONSULTA,
            nombre="Sin consentimiento",
            email="x@ejemplo.test",
            mensaje="Hola",
            consentimiento=False,
            consentimiento_en=timezone.now(),
        )
