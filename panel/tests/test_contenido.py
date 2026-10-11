"""Contenido del sitio desde el panel (ADM-10, PUB-06, SEG-06)."""

import re

import pytest

from sitio.models import DatosNegocio, Servicio
from solicitudes.models import Solicitud

pytestmark = pytest.mark.django_db

CONTENIDO = "/panel/contenido/"
SERVICIOS = "/panel/contenido/servicios/"
HTML_CRUDO = "<script>alert(1)</script>"
HTML_ESCAPADO = "&lt;script&gt;alert(1)&lt;/script&gt;"

DATOS = {
    "nombre_comercial": "Prevención Editada",
    "titular": "Titular editado",
    "bajada": "Bajada editada.",
    "presentacion": "Presentación editada.",
    "telefono": "+56 9 1111 2222",
    "email_publico": "hola@prevencion-editada.cl",
    "whatsapp": "",
    "ubicacion": "Curicó",
    "horario": "De 9 a 18",
    "instagram": "",
    "linkedin": "",
    "facebook": "",
    "politica_privacidad": "Política editada.",
}


def test_adm_10_el_menu_del_panel_lleva_a_contenido_del_sitio(cliente_http_admin):
    contenido = cliente_http_admin.get(CONTENIDO).content.decode()
    assert f'href="{CONTENIDO}" aria-current="page"' in contenido
    assert f'<a class="pestana" href="{SERVICIOS}">Servicios</a>' in contenido


def test_pub_06_cada_dato_pendiente_lleva_el_marcador_completar(cliente_http_admin, negocio):
    """Con todo completo no hay marcadores; cada dato que falta muestra el suyo."""
    completo = cliente_http_admin.get(CONTENIDO).content.decode()
    assert "[COMPLETAR]" not in completo

    DatosNegocio.objects.update(titular="", horario="[COMPLETAR]", politica_privacidad="")
    contenido = cliente_http_admin.get(CONTENIDO).content.decode()
    assert contenido.count('<span class="insignia insignia-advertencia">[COMPLETAR]</span>') == 3
    for campo in ("titular", "horario", "politica_privacidad"):
        antes = contenido.split(f'name="{campo}"')[0]
        assert antes.rstrip().count("[COMPLETAR]") >= 1, campo
    # Los opcionales nunca se marcan.
    antes_de_whatsapp = contenido.split('name="whatsapp"')[0].split('name="email_publico"')[1]
    assert "[COMPLETAR]" not in antes_de_whatsapp


def test_adm_10_editar_los_datos_del_negocio_cambia_el_sitio(cliente_http_admin, client):
    assert "Titular editado" not in client.get("/").content.decode()
    respuesta = cliente_http_admin.post(CONTENIDO, DATOS, follow=True)
    assert "Se guardaron los datos del negocio." in respuesta.content.decode()
    datos = DatosNegocio.objects.get()
    assert datos.nombre_comercial == "Prevención Editada" and datos.politica_privacidad
    assert DatosNegocio.objects.count() == 1

    inicio = client.get("/").content.decode()
    assert "Titular editado" in inicio and "Prevención Editada" in inicio
    assert "+56 9 1111 2222" in inicio and "<form" in inicio


@pytest.mark.parametrize(
    ("cambios", "error"),
    [
        ({"email_publico": "no-es-correo"}, "correo electrónico válida"),
        ({"instagram": "javascript:alert(1)"}, "URL válida"),
        ({"linkedin": "http://www.linkedin.com/company/x"}, "debe empezar con https://"),
        ({"nombre_comercial": "x" * 151}, "150 caracteres"),
    ],
)
def test_adm_10_los_datos_invalidos_se_rechazan_con_su_error(
    cliente_http_admin, negocio, cambios, error
):
    respuesta = cliente_http_admin.post(CONTENIDO, {**DATOS, **cambios})
    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200 and error in contenido
    assert DatosNegocio.objects.get().nombre_comercial == "Prevención de Prueba"


def test_adm_10_crear_un_servicio_lo_publica_al_final_con_su_direccion(
    cliente_http_admin, client, negocio, servicio
):
    respuesta = cliente_http_admin.post(
        SERVICIOS + "nuevo/",
        {
            "nombre": "  Asesoría   en Terreno ",
            "icono": "search-check",
            "resumen": "Visitas a faena.",
            "descripcion": "Línea uno.\nLínea dos.",
        },
        follow=True,
    )
    assert "Se creó el servicio Asesoría en Terreno." in respuesta.content.decode()
    nuevo = Servicio.objects.get(slug="asesoria-en-terreno")
    assert nuevo.nombre == "Asesoría en Terreno" and nuevo.orden == 2 and nuevo.activo
    pagina = client.get("/servicios/").content.decode()
    assert pagina.index("Servicio de prueba") < pagina.index("Asesoría en Terreno")
    assert "Línea uno.<br>Línea dos." in pagina

    # Renombrarlo no cambia su dirección: los enlaces que ya circulan siguen sirviendo.
    cliente_http_admin.post(
        f"{SERVICIOS}{nuevo.pk}/editar/",
        {"nombre": "Asesoría", "icono": "flame", "resumen": "", "descripcion": ""},
    )
    nuevo.refresh_from_db()
    assert nuevo.nombre == "Asesoría" and nuevo.slug == "asesoria-en-terreno"
    assert nuevo.icono == "flame"


def test_adm_10_el_nombre_no_se_repite_y_el_icono_sale_de_la_lista_fija(
    cliente_http_admin, servicio
):
    repetido = cliente_http_admin.post(
        SERVICIOS + "nuevo/", {"nombre": "SERVICIO DE PRUEBA", "icono": "flame"}
    )
    assert "Ya existe un servicio con ese nombre." in repetido.content.decode()
    otro_icono = cliente_http_admin.post(
        SERVICIOS + "nuevo/", {"nombre": "Otro", "icono": "../../etc/passwd"}
    )
    assert "Escoja una opción válida" in otro_icono.content.decode()
    assert Servicio.objects.count() == 1
    # Dos nombres que dan el mismo identificador reciben direcciones distintas.
    cliente_http_admin.post(
        SERVICIOS + "nuevo/", {"nombre": "Servicio de prueba!", "icono": "flame"}
    )
    assert set(Servicio.objects.values_list("slug", flat=True)) == {
        "servicio-de-prueba",
        "servicio-de-prueba-2",
    }


def test_adm_10_ordenar_los_servicios_con_subir_y_bajar(cliente_http_admin, servicio):
    segundo = Servicio.objects.create(nombre="Segundo", slug="segundo", orden=2)
    tercero = Servicio.objects.create(nombre="Tercero", slug="tercero", orden=3)

    def orden():
        return list(Servicio.objects.values_list("nombre", flat=True))

    cliente_http_admin.post(f"{SERVICIOS}{tercero.pk}/mover/", {"direccion": "subir"})
    assert orden() == ["Servicio de prueba", "Tercero", "Segundo"]
    cliente_http_admin.post(f"{SERVICIOS}{servicio.pk}/mover/", {"direccion": "bajar"})
    assert orden() == ["Tercero", "Servicio de prueba", "Segundo"]
    # En un extremo, o con una dirección inventada, no pasa nada.
    cliente_http_admin.post(f"{SERVICIOS}{tercero.pk}/mover/", {"direccion": "subir"})
    cliente_http_admin.post(f"{SERVICIOS}{segundo.pk}/mover/", {"direccion": "bajar"})
    cliente_http_admin.post(f"{SERVICIOS}{segundo.pk}/mover/", {"direccion": "al-medio"})
    assert orden() == ["Tercero", "Servicio de prueba", "Segundo"]
    assert list(Servicio.objects.values_list("orden", flat=True)) == [1, 2, 3]

    lista = cliente_http_admin.get(SERVICIOS).content.decode()
    botones = re.findall(r'value="(subir|bajar)" aria-label="[^"]+"( disabled)?', lista)
    assert botones[0] == ("subir", " disabled") and botones[-1] == ("bajar", " disabled")


def test_adm_10_desactivar_un_servicio_lo_saca_del_sitio_sin_tocar_sus_solicitudes(
    cliente_http_admin, client, negocio, servicio
):
    from django.utils import timezone

    solicitud = Solicitud.objects.create(
        tipo=Solicitud.Tipo.COTIZACION,
        nombre="Visitante",
        email="v@ejemplo.test",
        servicio=servicio,
        mensaje="Hola",
        consentimiento=True,
        consentimiento_en=timezone.now(),
    )
    url = f"{SERVICIOS}{servicio.pk}/estado/"
    respuesta = cliente_http_admin.post(url, {"activo": "no"}, follow=True)
    contenido = respuesta.content.decode()
    assert "Servicio de prueba dejó de mostrarse en el sitio." in contenido
    assert '<span class="insignia insignia-neutro">Inactivo</span>' in contenido
    assert "Servicio de prueba" not in client.get("/servicios/").content.decode()
    assert "Servicio de prueba" not in client.get("/cotizacion/").content.decode()
    solicitud.refresh_from_db()
    assert solicitud.servicio == servicio

    respuesta = cliente_http_admin.post(url, {"activo": "si"}, follow=True)
    assert "volvió a mostrarse en el sitio" in respuesta.content.decode()
    assert "Servicio de prueba" in client.get("/servicios/").content.decode()
    # No existe una ruta para borrar servicios.
    assert cliente_http_admin.post(f"{SERVICIOS}{servicio.pk}/eliminar/").status_code == 404
    assert cliente_http_admin.get(f"{SERVICIOS}999999/editar/").status_code == 404


def test_la_lista_sin_servicios_explica_como_empezar(cliente_http_admin):
    contenido = cliente_http_admin.get(SERVICIOS).content.decode()
    assert "Aún no hay servicios" in contenido and f'href="{SERVICIOS}nuevo/"' in contenido


def test_prueba_14_un_servicio_con_script_se_muestra_escapado_en_el_panel(cliente_http_admin):
    cliente_http_admin.post(
        SERVICIOS + "nuevo/",
        {
            "nombre": HTML_CRUDO,
            "icono": "flame",
            "resumen": f"Resumen {HTML_CRUDO}",
            "descripcion": f"Descripción {HTML_CRUDO}",
        },
    )
    servicio = Servicio.objects.get()
    assert servicio.nombre == HTML_CRUDO
    lista = cliente_http_admin.get(SERVICIOS).content.decode()
    edicion = cliente_http_admin.get(f"{SERVICIOS}{servicio.pk}/editar/").content.decode()
    for contenido in (lista, edicion):
        assert HTML_ESCAPADO in contenido and "<script>alert" not in contenido
    assert f'aria-label="Subir {HTML_ESCAPADO}"' in lista
    assert f"Descripción {HTML_ESCAPADO}" in edicion
    # También en el mensaje que confirma la acción.
    confirmacion = cliente_http_admin.post(
        f"{SERVICIOS}{servicio.pk}/estado/", {"activo": "no"}, follow=True
    ).content.decode()
    assert f"{HTML_ESCAPADO} dejó de mostrarse" in confirmacion
    assert "<script>alert" not in confirmacion


def test_seg_06_los_datos_del_negocio_con_html_se_muestran_escapados_en_el_panel(
    cliente_http_admin, negocio
):
    cliente_http_admin.post(
        CONTENIDO, {**DATOS, "titular": HTML_CRUDO, "politica_privacidad": HTML_CRUDO}
    )
    contenido = cliente_http_admin.get(CONTENIDO).content.decode()
    assert contenido.count(HTML_ESCAPADO) == 2 and "<script>alert" not in contenido


def test_la_politica_de_prueba_se_advierte_en_el_panel(cliente_http_admin, negocio):
    DatosNegocio.objects.update(politica_privacidad="TEXTO DE PRUEBA\n\nNo publicar.")
    contenido = cliente_http_admin.get(CONTENIDO).content.decode()
    assert "Este es un texto de prueba." in contenido
