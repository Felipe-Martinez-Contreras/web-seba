"""Antispam sin servicios externos (SOL-04) y prueba 12 de la sección 12.2."""

import pytest
from django.core import mail
from django.test import Client

from conftest import datos_de_consulta, datos_de_cotizacion, marca_de_hace
from solicitudes import antispam
from solicitudes.models import Solicitud

pytestmark = pytest.mark.django_db

AVISO = "No pudimos procesar su solicitud. Inténtelo nuevamente en unos minutos."


def _descartada(respuesta):
    """El envío no se guardó ni se notificó, y la respuesta es el mismo formulario con el
    aviso neutro y lo escrito."""
    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert AVISO in contenido and 'role="alert"' in contenido
    assert 'value="Visitante de Prueba"' in contenido
    assert "Necesito información sobre sus servicios." in contenido
    assert not Solicitud.objects.exists() and mail.outbox == []
    return contenido


def test_prueba_12_sin_token_csrf_los_formularios_publicos_responden_403(negocio, servicio):
    cliente = Client(enforce_csrf_checks=True)
    for ruta, datos in (
        ("/contacto/", datos_de_consulta()),
        ("/cotizacion/", datos_de_cotizacion()),
    ):
        respuesta = cliente.post(ruta, datos)
        assert respuesta.status_code == 403, ruta
        assert "No pudimos procesar el formulario" in respuesta.content.decode(), ruta
    assert not Solicitud.objects.exists() and mail.outbox == []

    # Con el token de la página, el mismo envío sí pasa.
    pagina = cliente.get("/contacto/")
    token = pagina.cookies["csrftoken"].value
    respuesta = cliente.post("/contacto/", datos_de_consulta(), HTTP_X_CSRFTOKEN=token)
    assert respuesta.status_code == 302 and Solicitud.objects.count() == 1


def test_prueba_12_el_campo_trampa_descarta_el_envio(client, negocio, servicio):
    contenido = _descartada(
        client.post("/contacto/", datos_de_consulta(sitio_web="https://spam.example"))
    )
    # Lo escrito en el campo trampa no vuelve al formulario.
    assert "spam.example" not in contenido
    assert 'name="sitio_web" value=""' in contenido
    _descartada(client.post("/cotizacion/", datos_de_cotizacion(sitio_web="x")))


def test_el_campo_trampa_no_lo_ven_las_personas_ni_lo_alcanza_el_teclado(client, negocio):
    contenido = client.get("/contacto/").content.decode()
    assert '<div class="trampa" aria-hidden="true">' in contenido
    assert 'name="sitio_web" value="" tabindex="-1" autocomplete="off"' in contenido
    assert "style=" not in contenido


@pytest.mark.parametrize(
    "marca",
    [
        pytest.param(lambda: marca_de_hace(1), id="menos de 3 segundos"),
        pytest.param(lambda: "", id="sin marca"),
        pytest.param(lambda: marca_de_hace(30)[:-3] + "abc", id="firma alterada"),
        pytest.param(lambda: "1700000000:firmafalsa", id="marca inventada"),
        pytest.param(lambda: marca_de_hace(-600), id="marca del futuro"),
        pytest.param(lambda: marca_de_hace(25 * 3600), id="formulario abierto más de un día"),
    ],
)
def test_prueba_12_el_tiempo_minimo_y_la_marca_firmada(client, negocio, marca):
    contenido = _descartada(client.post("/contacto/", datos_de_consulta(marca=marca())))
    # El formulario vuelve con una marca nueva y válida, para poder reintentar.
    nueva = contenido.split('name="marca" value="')[1].split('"')[0]
    assert antispam._edad(nueva) is not None and antispam._edad(nueva) < 5


def test_con_tres_segundos_o_mas_el_envio_pasa(client, negocio, settings):
    assert settings.SOLICITUDES_TIEMPO_MINIMO_SEGUNDOS == 3
    assert client.post("/contacto/", datos_de_consulta(marca=marca_de_hace(4))).status_code == 302
    assert Solicitud.objects.count() == 1


def test_al_corregir_un_error_se_conserva_la_marca_original(client, negocio):
    """Quien corrige un campo y reenvía de inmediato no cae en el tiempo mínimo."""
    marca = marca_de_hace(40)
    respuesta = client.post("/contacto/", datos_de_consulta(marca=marca, mensaje=""))
    assert f'name="marca" value="{marca}"' in respuesta.content.decode()
    assert client.post("/contacto/", datos_de_consulta(marca=marca)).status_code == 302


def test_prueba_12_el_limite_por_ip_descarta_desde_el_sexto_envio(client, negocio, servicio):
    for numero in range(5):
        respuesta = client.post("/contacto/", datos_de_consulta(nombre=f"Persona {numero}"))
        assert respuesta.status_code == 302, numero
    assert Solicitud.objects.count() == 5

    # El sexto, por cualquiera de los dos formularios, no se guarda.
    for ruta, datos in (
        ("/contacto/", datos_de_consulta()),
        ("/cotizacion/", datos_de_cotizacion()),
    ):
        respuesta = client.post(ruta, datos)
        assert respuesta.status_code == 200 and AVISO in respuesta.content.decode()
    assert Solicitud.objects.count() == 5 and len(mail.outbox) == 5

    # Otra IP no se ve afectada.
    assert (
        client.post("/contacto/", datos_de_consulta(), REMOTE_ADDR="203.0.113.9").status_code == 302
    )
    assert Solicitud.objects.count() == 6


def test_el_limite_es_configurable_y_no_lo_gastan_los_envios_invalidos(client, negocio, settings):
    settings.SOLICITUDES_MAXIMO_POR_HORA_IP = 1
    # Errores de validación y descartes por la trampa no consumen el cupo.
    for _ in range(3):
        client.post("/contacto/", datos_de_consulta(mensaje=""))
        client.post("/contacto/", datos_de_consulta(sitio_web="x"))
    assert client.post("/contacto/", datos_de_consulta()).status_code == 302
    assert client.post("/contacto/", datos_de_consulta()).status_code == 200
    assert Solicitud.objects.count() == 1


def test_un_encabezado_del_proxy_no_esquiva_el_limite_si_no_viene_de_un_proxy_de_confianza(
    client, negocio, settings
):
    """AUT-04: la IP es la de la conexión, salvo que el proxy de confianza diga otra cosa."""
    settings.SOLICITUDES_MAXIMO_POR_HORA_IP = 1
    assert client.post("/contacto/", datos_de_consulta()).status_code == 302
    for numero in range(3):
        respuesta = client.post(
            "/contacto/", datos_de_consulta(), HTTP_X_FORWARDED_FOR=f"198.51.100.{numero}"
        )
        assert respuesta.status_code == 200
    assert Solicitud.objects.count() == 1


def test_el_aviso_es_el_mismo_para_todos_los_motivos_y_ofrece_el_contacto(
    client, negocio, settings
):
    """SOL-04: el descarte no explica su motivo. Con teléfono o correo registrados, los
    ofrece como alternativa."""
    settings.SOLICITUDES_MAXIMO_POR_HORA_IP = 0
    respuestas = [
        client.post("/contacto/", datos_de_consulta(sitio_web="x")),
        client.post("/contacto/", datos_de_consulta(marca=marca_de_hace(0))),
        client.post("/contacto/", datos_de_consulta()),
    ]
    avisos = set()
    for respuesta in respuestas:
        contenido = respuesta.content.decode()
        avisos.add(contenido.split('role="alert"')[1].split("</div>")[0])
    assert len(avisos) == 1
    aviso = avisos.pop()
    assert AVISO in aviso
    assert "También puede contactarnos al teléfono +56 9 8765 4321" in aviso
    assert "o al correo contacto@prevencion-de-prueba.cl." in aviso
    for palabra in ("spam", "rápido", "límite", "robot", "IP"):
        assert palabra not in aviso, palabra

    negocio.telefono = negocio.email_publico = ""
    negocio.save()
    contenido = client.post("/contacto/", datos_de_consulta(sitio_web="x")).content.decode()
    assert AVISO in contenido and "También puede contactarnos" not in contenido


def test_el_descarte_solo_registra_que_control_actuo(client, negocio, caplog):
    with caplog.at_level("INFO", logger="solicitudes.antispam"):
        client.post("/contacto/", datos_de_consulta(sitio_web="x"))
    (registro,) = caplog.records
    assert registro.getMessage() == "Solicitud descartada por el antispam: campo trampa"
    assert "visitante@ejemplo.test" not in caplog.text and "Visitante" not in caplog.text


def test_la_ip_del_visitante_no_se_guarda_en_la_solicitud(client, negocio):
    client.post("/contacto/", datos_de_consulta(), REMOTE_ADDR="203.0.113.77")
    campos = {campo.name for campo in Solicitud._meta.get_fields()}
    assert "ip" not in campos
    assert "203.0.113.77" not in str(Solicitud.objects.values().get())


def captcha_que_rechaza(request):
    return False


def captcha_que_acepta(request):
    return True


def test_el_punto_de_extension_del_captcha_esta_desactivado_por_defecto(client, negocio, settings):
    assert settings.SOLICITUDES_CAPTCHA == ""
    assert "captcha" not in client.get("/contacto/").content.decode().lower()

    settings.SOLICITUDES_CAPTCHA = "solicitudes.tests.test_antispam.captcha_que_rechaza"
    _descartada(client.post("/contacto/", datos_de_consulta()))
    settings.SOLICITUDES_CAPTCHA = "solicitudes.tests.test_antispam.captcha_que_acepta"
    assert client.post("/contacto/", datos_de_consulta()).status_code == 302
