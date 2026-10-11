"""Bandeja y detalle de solicitudes en el panel (SOL-09, SOL-10, ADM-02, AUD-01)."""

import datetime

import pytest
from django.core import mail
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import Accion
from solicitudes.models import Solicitud

pytestmark = pytest.mark.django_db

CONSULTAS = "/panel/solicitudes/consultas/"
COTIZACIONES = "/panel/solicitudes/cotizaciones/"
HTML_CRUDO = "<script>alert(1)</script>"
HTML_ESCAPADO = "&lt;script&gt;alert(1)&lt;/script&gt;"


def _solicitud(nombre="Visitante de Prueba", *, dias=0, **campos):
    datos = {
        "tipo": Solicitud.Tipo.CONSULTA,
        "nombre": nombre,
        "email": "visitante@ejemplo.test",
        "mensaje": "Mensaje de prueba.",
        "consentimiento": True,
        "consentimiento_en": timezone.now(),
        "notificacion": Solicitud.Notificacion.ENVIADA,
        **campos,
    }
    solicitud = Solicitud.objects.create(**datos)
    if dias:
        fecha = timezone.now() - datetime.timedelta(days=dias)
        Solicitud.objects.filter(pk=solicitud.pk).update(creado_en=fecha)
    return solicitud


def _nombres(contenido):
    import re

    return re.findall(r'href="/panel/solicitudes/[0-9a-f-]{36}/">([^<]+)</a>', contenido)


def test_sol_09_la_bandeja_separa_consultas_y_cotizaciones_en_pestanas(
    cliente_http_admin, servicio
):
    _solicitud("Consulta Uno")
    _solicitud("Cotización Uno", tipo=Solicitud.Tipo.COTIZACION, servicio=servicio)
    consultas = cliente_http_admin.get(CONSULTAS).content.decode()
    assert _nombres(consultas) == ["Consulta Uno"]
    assert f'<a class="pestana" href="{CONSULTAS}" aria-current="page">Consultas</a>' in consultas
    assert f'<a class="pestana" href="{COTIZACIONES}">Cotizaciones</a>' in consultas
    assert '<th scope="col">Servicio</th>' not in consultas

    cotizaciones = cliente_http_admin.get(COTIZACIONES).content.decode()
    assert _nombres(cotizaciones) == ["Cotización Uno"]
    assert '<th scope="col">Servicio</th>' in cotizaciones and "Servicio de prueba" in cotizaciones
    # El menú del panel marca Solicitudes como la sección activa.
    assert f'href="{CONSULTAS}" aria-current="page"' in cotizaciones


def test_sol_09_cada_estado_lleva_su_insignia_con_texto_y_la_notificacion_se_ve(
    cliente_http_admin,
):
    for estado in Solicitud.Estado:
        _solicitud(f"Con estado {estado.label}", estado=estado)
    _solicitud("Sin aviso", notificacion=Solicitud.Notificacion.FALLIDA)
    contenido = cliente_http_admin.get(CONSULTAS).content.decode()
    for clase, texto in (
        ("insignia-error", "Pendiente"),
        ("insignia-info", "En proceso"),
        ("insignia-exito", "Resuelta"),
        ("insignia-neutro", "Descartada"),
        ("insignia-error", "Fallida"),
        ("insignia-exito", "Enviada"),
    ):
        assert f'<span class="insignia {clase}">{texto}</span>' in contenido, texto


def test_sol_09_filtros_por_estado_y_fechas_busqueda_y_orden(cliente_http_admin):
    _solicitud("Ana Antigua", dias=40, empresa="Constructora Norte")
    _solicitud("Bruno Reciente", dias=2, estado=Solicitud.Estado.RESUELTA)
    _solicitud("Carla de Hoy", email="carla@minera-sur.test")

    def ver(consulta=""):
        return _nombres(cliente_http_admin.get(CONSULTAS + consulta).content.decode())

    assert ver() == ["Carla de Hoy", "Bruno Reciente", "Ana Antigua"]
    assert ver("?orden=antiguas") == ["Ana Antigua", "Bruno Reciente", "Carla de Hoy"]
    assert ver("?estado=resuelta") == ["Bruno Reciente"]
    assert ver("?q=bruno") == ["Bruno Reciente"]
    assert ver("?q=minera-sur") == ["Carla de Hoy"]
    assert ver("?q=constructora+norte") == ["Ana Antigua"]
    hace_diez = (timezone.localdate() - datetime.timedelta(days=10)).isoformat()
    assert ver(f"?desde={hace_diez}") == ["Carla de Hoy", "Bruno Reciente"]
    assert ver(f"?hasta={hace_diez}") == ["Ana Antigua"]
    assert ver(f"?desde={hace_diez}&estado=resuelta&orden=antiguas") == ["Bruno Reciente"]

    sin_resultados = cliente_http_admin.get(CONSULTAS + "?q=nadie").content.decode()
    assert "Sin resultados" in sin_resultados and "Quitar filtros" in sin_resultados
    # Un filtro inválido no muestra nada: mostrar todo sugeriría que se aplicó.
    invalido = cliente_http_admin.get(CONSULTAS + "?desde=ayer").content.decode()
    assert "Revise los filtros" in invalido and _nombres(invalido) == []
    alreves = cliente_http_admin.get(
        CONSULTAS + f"?desde={timezone.localdate().isoformat()}&hasta={hace_diez}"
    ).content.decode()
    assert "La fecha final no puede ser anterior a la inicial." in alreves


def test_sol_09_la_bandeja_pagina_de_a_25_sin_consultas_por_fila(
    cliente_http_admin, servicio, django_assert_max_num_queries
):
    for numero in range(30):
        _solicitud(f"Persona {numero:02d}", tipo=Solicitud.Tipo.COTIZACION, servicio=servicio)
    with django_assert_max_num_queries(12):
        primera = cliente_http_admin.get(COTIZACIONES).content.decode()
    assert len(_nombres(primera)) == 25 and "Página 1 de 2" in primera
    segunda = cliente_http_admin.get(COTIZACIONES + "?page=2&orden=antiguas").content.decode()
    assert len(_nombres(segunda)) == 5
    # La paginación conserva el orden elegido.
    assert "orden=antiguas" in segunda and "page=1" in segunda


def test_la_bandeja_vacia_explica_que_va_a_aparecer(cliente_http_admin):
    assert "Aún no hay consultas" in cliente_http_admin.get(CONSULTAS).content.decode()
    assert (
        "Aún no hay solicitudes de cotización"
        in cliente_http_admin.get(COTIZACIONES).content.decode()
    )


def test_sol_10_el_detalle_muestra_todos_los_datos_con_fecha_y_hora(cliente_http_admin, servicio):
    solicitud = _solicitud(
        tipo=Solicitud.Tipo.COTIZACION,
        telefono="+56 9 1234 5678",
        empresa="Constructora de Prueba Ltda.",
        servicio=servicio,
        trabajadores=Solicitud.Trabajadores.MAS_DE_100,
        comuna="Talca",
        mensaje="Primera línea.\nSegunda línea.",
    )
    contenido = cliente_http_admin.get(f"/panel/solicitudes/{solicitud.pk}/").content.decode()
    local = timezone.localtime(solicitud.creado_en)
    assert f"Recibida el {local:%d-%m-%Y} a las {local:%H:%M}." in contenido
    for dato in (
        "Cotización de Visitante de Prueba",
        'href="mailto:visitante@ejemplo.test"',
        "+56 9 1234 5678",
        "Constructora de Prueba Ltda.",
        "Servicio de prueba",
        "Más de 100",
        "Talca",
        "Primera línea.<br>Segunda línea.",
        f"Aceptada el {local:%d-%m-%Y}",
        "La plataforma no envía mensajes al visitante.",
    ):
        assert dato in contenido, dato
    assert f'href="{COTIZACIONES}">Cotizaciones</a>' in contenido
    # No hay mensajería interna: ningún formulario para responder al visitante.
    assert "Responder" not in contenido


def test_sol_10_el_cambio_de_estado_queda_en_la_solicitud_y_en_la_auditoria(cliente_http_admin):
    solicitud = _solicitud()
    url = f"/panel/solicitudes/{solicitud.pk}/estado/"
    respuesta = cliente_http_admin.post(url, {"estado": "en_proceso"}, follow=True)
    assert "La solicitud quedó como En proceso." in respuesta.content.decode()
    cliente_http_admin.post(url, {"estado": "resuelta"})
    solicitud.refresh_from_db()
    assert solicitud.estado == Solicitud.Estado.RESUELTA

    def eventos():
        return list(EventoAuditoria.objects.filter(accion=Accion.SOLICITUD_ESTADO).order_by("id"))

    assert [evento.detalle for evento in eventos()] == [
        "Consulta: Pendiente → En proceso",
        "Consulta: En proceso → Resuelta",
    ]
    assert all(evento.objeto_uuid == solicitud.pk and evento.actor for evento in eventos())
    assert all(evento.objeto_tipo == "solicitud" and evento.ip for evento in eventos())
    # El evento no lleva datos del visitante.
    assert "Visitante" not in "".join(evento.detalle for evento in eventos())

    # Repetir el mismo estado, o enviar uno inventado, no cambia ni registra nada.
    cliente_http_admin.post(url, {"estado": "resuelta"})
    cliente_http_admin.post(url, {"estado": "inventado"})
    solicitud.refresh_from_db()
    assert solicitud.estado == Solicitud.Estado.RESUELTA and len(eventos()) == 2
    # Y se puede descartar o reabrir.
    cliente_http_admin.post(url, {"estado": "descartada"})
    cliente_http_admin.post(url, {"estado": "pendiente"})
    assert [evento.detalle for evento in eventos()][2:] == [
        "Consulta: Resuelta → Descartada",
        "Consulta: Descartada → Pendiente",
    ]


def test_sol_10_las_notas_internas_se_guardan_y_solo_las_ve_el_panel(cliente_http_admin, client):
    solicitud = _solicitud()
    url = f"/panel/solicitudes/{solicitud.pk}/notas/"
    respuesta = cliente_http_admin.post(
        url, {"notas_internas": f"Llamar el lunes {HTML_CRUDO}"}, follow=True
    )
    contenido = respuesta.content.decode()
    assert "Se guardaron las notas internas." in contenido
    assert f"Llamar el lunes {HTML_ESCAPADO}" in contenido and "<script>alert" not in contenido
    solicitud.refresh_from_db()
    assert solicitud.notas_internas == f"Llamar el lunes {HTML_CRUDO}"
    assert mail.outbox == []

    respuesta = cliente_http_admin.post(url, {"notas_internas": "x" * 5001}, follow=True)
    assert "Las notas no se guardaron" in respuesta.content.decode()
    solicitud.refresh_from_db()
    assert solicitud.notas_internas.startswith("Llamar el lunes")


def test_una_solicitud_inexistente_responde_404_en_todas_sus_rutas(cliente_http_admin):
    base = "/panel/solicitudes/00000000-0000-4000-8000-000000000000/"
    assert cliente_http_admin.get(base).status_code == 404
    for accion in ("estado/", "notas/", "reintentar/"):
        assert cliente_http_admin.post(base + accion, {"estado": "resuelta"}).status_code == 404
        assert cliente_http_admin.get(base + accion).status_code == 405


def test_prueba_14_los_datos_del_visitante_y_del_servicio_se_muestran_escapados_en_el_panel(
    cliente_http_admin, servicio
):
    servicio.nombre = HTML_CRUDO
    servicio.save()
    solicitud = _solicitud(
        f"Nombre {HTML_CRUDO}",
        tipo=Solicitud.Tipo.COTIZACION,
        servicio=servicio,
        empresa=f"Empresa {HTML_CRUDO}",
        comuna=f"Comuna {HTML_CRUDO}",
        mensaje=f"Mensaje {HTML_CRUDO}",
        notificacion=Solicitud.Notificacion.FALLIDA,
        notificacion_error=f"Error {HTML_CRUDO}",
    )
    for ruta in (COTIZACIONES, f"/panel/solicitudes/{solicitud.pk}/", "/panel/"):
        contenido = cliente_http_admin.get(ruta).content.decode()
        assert "<script>alert" not in contenido, ruta
        assert f"Nombre {HTML_ESCAPADO}" in contenido, ruta
    detalle = cliente_http_admin.get(f"/panel/solicitudes/{solicitud.pk}/").content.decode()
    for dato in ("Empresa", "Comuna", "Mensaje", "Error: Error"):
        assert f"{dato} {HTML_ESCAPADO}" in detalle, dato
    assert f">{HTML_ESCAPADO}</dd>" in detalle


def test_adm_02_el_inicio_cuenta_las_pendientes_y_lista_las_recientes(cliente_http_admin):
    vacio = cliente_http_admin.get("/panel/").content.decode()
    assert "Aún no hay solicitudes" in vacio
    assert "Notificaciones por correo fallidas" not in vacio

    _solicitud("Consulta pendiente")
    _solicitud("Consulta resuelta", estado=Solicitud.Estado.RESUELTA)
    for numero in range(3):
        _solicitud(
            f"Cotización {numero}",
            tipo=Solicitud.Tipo.COTIZACION,
            notificacion=Solicitud.Notificacion.FALLIDA,
        )
    _solicitud("La más antigua", dias=9)
    contenido = cliente_http_admin.get("/panel/").content.decode()

    def indicador(etiqueta):
        return contenido.split(f">{etiqueta}</p>")[1].split("</p>")[0].split(">")[-1]

    assert indicador("Consultas pendientes") == "2"
    assert indicador("Cotizaciones pendientes") == "3"
    assert f'href="{CONSULTAS}?estado=pendiente"' in contenido
    assert f'href="{COTIZACIONES}?estado=pendiente"' in contenido
    assert "Notificaciones por correo fallidas: 3" in contenido
    # Las cinco más recientes, con su tipo y estado; la sexta queda fuera.
    assert len(_nombres(contenido)) == 5 and "La más antigua" not in contenido
    assert '<td data-etiqueta="Tipo">Cotización</td>' in contenido
    assert '<span class="insignia insignia-exito">Resuelta</span>' in contenido
