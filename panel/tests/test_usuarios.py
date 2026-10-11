"""Usuarios de un cliente en el panel: alta, estados, enlaces, edición y corte (ADM-06)."""

import re
from datetime import timedelta

import pytest
from django.contrib.sessions.models import Session
from django.core import mail
from django.test import Client
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import Accion
from conftest import CLAVE, RUT_CLIENTE_A, entrar
from cuentas import services
from cuentas.estados import anotar_estados
from cuentas.models import EnlaceAcceso, Usuario

pytestmark = pytest.mark.django_db

ACTIVACION = EnlaceAcceso.Tipo.ACTIVACION
RESTABLECIMIENTO = EnlaceAcceso.Tipo.RESTABLECIMIENTO
NUEVA = "tornillo-violeta-marea-88"
PERSONA = {"rut": "5.126.663-3", "nombre": "Persona de Prueba", "email": "persona@ejemplo.test"}


def _usuarios(empresa):
    return f"/panel/clientes/{empresa.pk}/usuarios/"


def _de(usuario, accion):
    return f"/panel/clientes/{usuario.empresa_id}/usuarios/{usuario.uuid}/{accion}/"


def _enlace_de(contenido):
    return re.search(r'id="enlace-de-acceso" type="text" value="([^"]+)"', contenido).group(1)


def _ruta(url):
    return url.removeprefix("http://testserver")


# --- Alta y envío del enlace ------------------------------------------------------------


def test_con_correo_configurado_el_enlace_se_envia_y_ademas_se_muestra(
    cliente_http_admin, empresa_a
):
    formulario = cliente_http_admin.get(_usuarios(empresa_a) + "nuevo/").content.decode()
    assert 'name="por_correo"' in formulario and "El correo no está configurado" not in formulario

    respuesta = cliente_http_admin.post(
        _usuarios(empresa_a) + "nuevo/", {**PERSONA, "por_correo": "on"}
    )
    contenido = respuesta.content.decode()
    url = _enlace_de(contenido)
    assert "El enlace también se envió por correo a persona@ejemplo.test." in contenido

    assert len(mail.outbox) == 1
    mensaje = mail.outbox[0]
    assert mensaje.to == ["persona@ejemplo.test"] and mensaje.subject == "Active su cuenta"
    assert url in mensaje.body and "Persona de Prueba" in mensaje.body
    assert "una sola vez" in mensaje.body and mensaje.attachments == []
    enlace = EnlaceAcceso.objects.get()
    assert enlace.envio == EnlaceAcceso.Envio.ENVIADA and enlace.envio_error == ""
    correo = EventoAuditoria.objects.get(accion=Accion.ENLACE_CORREO)
    assert correo.detalle == "Enviada" and correo.empresa == empresa_a
    # Ni el correo ni la auditoría llevan una contraseña: nadie la conoce todavía.
    assert not Usuario.objects.get(rut="51266633").has_usable_password()


def test_sin_marcar_la_casilla_o_sin_correo_registrado_no_se_envia_nada(
    cliente_http_admin, empresa_a
):
    cliente_http_admin.post(_usuarios(empresa_a) + "nuevo/", PERSONA)
    respuesta = cliente_http_admin.post(
        _usuarios(empresa_a) + "nuevo/",
        {"rut": "9.876.543-3", "nombre": "Sin Correo", "email": "", "por_correo": "on"},
    )
    assert "se envió" not in respuesta.content.decode()
    assert mail.outbox == []
    assert set(EnlaceAcceso.objects.values_list("envio", flat=True)) == {""}
    assert not EventoAuditoria.objects.filter(accion=Accion.ENLACE_CORREO).exists()


def test_si_el_correo_falla_el_panel_lo_informa_y_el_enlace_igual_sirve(
    cliente_http_admin, empresa_a, settings
):
    """AUT-06 y R4: el panel nunca dice "enviado" cuando el envío falló."""
    settings.MAILERS = {"default": {"BACKEND": "cuentas.tests.test_recuperacion.BackendQueFalla"}}
    respuesta = cliente_http_admin.post(
        _usuarios(empresa_a) + "nuevo/", {**PERSONA, "por_correo": "on"}
    )
    contenido = respuesta.content.decode()
    assert "No se pudo enviar el correo" in contenido and "se envió" not in contenido
    assert 'role="alert"' in contenido
    enlace = EnlaceAcceso.objects.get()
    assert enlace.envio == EnlaceAcceso.Envio.FALLIDA and enlace.envio_error
    assert EventoAuditoria.objects.get(accion=Accion.ENLACE_CORREO).detalle == "Fallida"
    assert Client().get(_ruta(_enlace_de(contenido))).status_code == 200


@pytest.mark.parametrize(
    ("datos", "mensaje"),
    [
        ({"rut": "5.126.663-4"}, "Ingrese un RUT válido"),
        ({"rut": "11.111.111-1"}, "Ya existe una cuenta con ese RUT."),
        ({"rut": "12.345.678-5"}, "Ya existe una cuenta con ese RUT."),
        ({"nombre": ""}, "Este campo es obligatorio."),
        ({"email": "no-es-correo"}, "correo"),
    ],
)
def test_los_datos_invalidos_no_crean_la_cuenta(
    cliente_http_admin, cliente_a, empresa_b, datos, mensaje
):
    """El RUT es único en toda la plataforma: tampoco puede repetir el de otra empresa ni
    el de un administrador."""
    respuesta = cliente_http_admin.post(_usuarios(empresa_b) + "nuevo/", {**PERSONA, **datos})
    assert respuesta.status_code == 200
    assert mensaje in respuesta.content.decode()
    assert Usuario.objects.count() == 2 and not EnlaceAcceso.objects.exists()
    assert mail.outbox == []


def test_en_un_cliente_inactivo_la_cuenta_se_crea_pero_no_se_genera_enlace(
    cliente_http_admin, empresa_a
):
    empresa_a.activa = False
    empresa_a.save()
    respuesta = cliente_http_admin.post(_usuarios(empresa_a) + "nuevo/", PERSONA, follow=True)
    assert "el cliente está inactivo" in respuesta.content.decode()
    assert Usuario.objects.filter(rut="51266633").exists()
    assert not EnlaceAcceso.objects.exists() and mail.outbox == []


# --- Estados ----------------------------------------------------------------------------


def test_la_lista_muestra_los_cuatro_estados_y_el_ultimo_acceso(
    cliente_http_admin, empresa_a, cliente_a_activo, settings
):
    settings.ACCESO_INTENTOS_MAXIMOS = 2
    crear = Usuario.objects.create_user
    cliente = Usuario.Rol.CLIENTE
    pendiente = crear("5.126.663-3", nombre="Pendiente Uno", rol=cliente, empresa=empresa_a)
    vencido = crear("9.876.543-3", nombre="Pendiente Vencido", rol=cliente, empresa=empresa_a)
    sin_enlace = crear("1-9", nombre="Pendiente Sin Enlace", rol=cliente, empresa=empresa_a)
    inactivo = crear("2-7", nombre="Inactivo Uno", rol=cliente, empresa=empresa_a, password=CLAVE)
    bloqueado = crear("3-5", nombre="Bloqueado Uno", rol=cliente, empresa=empresa_a, password=CLAVE)
    inactivo.is_active = False
    inactivo.save()
    services.generar_enlace(pendiente, ACTIVACION)
    enlace, _ = services.generar_enlace(vencido, ACTIVACION)
    EnlaceAcceso.objects.filter(pk=enlace.pk).update(
        expira_en=timezone.now() - timedelta(minutes=1)
    )
    entrar(Client(), RUT_CLIENTE_A)
    visitante = Client()
    for _ in range(2):
        entrar(visitante, "3-5", "clave-equivocada-123")

    estados = {
        u.nombre: (u.estado.clave, u.estado.tono, u.estado.detalle)
        for u in anotar_estados(empresa_a.usuarios.all())
    }
    assert estados["Cliente de A"] == ("activo", "exito", "")
    assert estados["Inactivo Uno"] == ("inactivo", "neutro", "")
    assert estados["Bloqueado Uno"] == ("bloqueado", "error", "Por intentos fallidos")
    assert estados["Pendiente Uno"][:2] == ("pendiente", "advertencia")
    assert estados["Pendiente Uno"][2].startswith("Enlace vigente hasta el ")
    assert estados["Pendiente Vencido"][2] == "Enlace de activación vencido"
    assert estados["Pendiente Sin Enlace"][2] == "Sin enlace de activación vigente"
    assert sin_enlace.last_login is None

    contenido = cliente_http_admin.get(_usuarios(empresa_a)).content.decode()
    # El estado se lee como texto, con su tono al lado.
    for tono, texto in (
        ("exito", "Activo"),
        ("neutro", "Inactivo"),
        ("error", "Bloqueado"),
        ("advertencia", "Pendiente"),
    ):
        assert f'<span class="insignia insignia-{tono}">{texto}</span>' in contenido
    assert "Enlace de activación vencido" in contenido
    assert "Nunca" in contenido
    assert (
        timezone.localtime(Usuario.objects.get(rut="111111111").last_login).strftime(
            "%d-%m-%Y %H:%M"
        )
        in contenido
    )
    # Desbloquear solo se ofrece para la cuenta bloqueada.
    assert contenido.count("/desbloquear/") == 1 and _de(bloqueado, "desbloquear") in contenido
    # A la cuenta inactiva no se le ofrece generar enlace, sí reactivarla.
    assert _de(inactivo, "enlace") not in contenido and "Reactivar" in contenido
    assert "Generar enlace de activación" in contenido
    assert "Generar enlace de restablecimiento" in contenido


def test_la_lista_no_hace_consultas_por_usuario(
    cliente_http_admin, empresa_a, django_assert_max_num_queries
):
    from core import rut

    for n in range(30):
        cuerpo = 5_000_000 + n
        Usuario.objects.create_user(
            f"{cuerpo}{rut.digito_verificador(cuerpo)}",
            nombre=f"Persona {n:02d}",
            rol=Usuario.Rol.CLIENTE,
            empresa=empresa_a,
        )
    with django_assert_max_num_queries(14):
        contenido = cliente_http_admin.get(_usuarios(empresa_a)).content.decode()
    assert contenido.count('data-etiqueta="RUT"') == 25 and "Página 1 de 2" in contenido


# --- Enlaces desde la lista -------------------------------------------------------------


def test_generar_un_enlace_nuevo_revoca_el_anterior_y_es_de_un_solo_uso(
    cliente_http_admin, cliente_a
):
    """Prueba 8 de la sección 12.2 con enlaces generados desde el panel."""
    url = _de(cliente_a, "enlace")
    assert cliente_http_admin.get(url).status_code == 405
    primero = _ruta(_enlace_de(cliente_http_admin.post(url).content.decode()))
    respuesta = cliente_http_admin.post(url)
    assert "Enlace de activación" in respuesta.content.decode()
    assert "Se creó la cuenta" not in respuesta.content.decode()
    segundo = _ruta(_enlace_de(respuesta.content.decode()))
    assert primero != segundo and segundo.startswith("/activar/")

    assert Client().get(primero).status_code == 404
    persona = Client()
    assert (
        persona.post(segundo, {"new_password1": NUEVA, "new_password2": NUEVA}).status_code == 302
    )
    assert Client().get(segundo).status_code == 404
    alterado = segundo[:-2] + ("A" if segundo[-2] != "A" else "B") + "/"
    assert Client().get(alterado).status_code == 404

    assert EventoAuditoria.objects.filter(accion=Accion.ENLACE_GENERADO).count() == 2
    token = segundo.removeprefix("/activar/").rstrip("/")
    rastros = "".join(EventoAuditoria.objects.values_list("detalle", flat=True)) + "".join(
        EnlaceAcceso.objects.values_list("token_hash", flat=True)
    )
    assert token not in rastros


def test_para_una_cuenta_activa_el_enlace_es_de_restablecimiento_y_cierra_sus_sesiones(
    cliente_http_admin, cliente_a_activo
):
    abierta = Client()
    entrar(abierta, RUT_CLIENTE_A)
    respuesta = cliente_http_admin.post(_de(cliente_a_activo, "enlace"), {"por_correo": "si"})
    contenido = respuesta.content.decode()
    assert "Enlace para definir una contraseña nueva" in contenido
    ruta = _ruta(_enlace_de(contenido))
    assert ruta.startswith("/restablecer/")
    assert EnlaceAcceso.objects.get().tipo == RESTABLECIMIENTO
    assert mail.outbox[0].subject == "Defina una contraseña nueva"
    assert mail.outbox[0].to == ["cliente.a@ejemplo.test"]
    # Generarlo no cambia nada todavía: la contraseña anterior sigue valiendo.
    assert abierta.get("/portal/").status_code == 200

    Client().post(ruta, {"new_password1": NUEVA, "new_password2": NUEVA})
    assert abierta.get("/portal/").status_code == 302


def test_no_se_genera_enlace_para_una_cuenta_inactiva(cliente_http_admin, cliente_a):
    cliente_a.is_active = False
    cliente_a.save()
    respuesta = cliente_http_admin.post(_de(cliente_a, "enlace"), follow=True)
    assert "No se generó el enlace" in respuesta.content.decode()
    assert not EnlaceAcceso.objects.exists()


# --- Edición y estado -------------------------------------------------------------------


def test_editar_cambia_nombre_y_correo_y_el_rut_solo_mientras_esta_pendiente(
    cliente_http_admin, cliente_a, cliente_b_activo
):
    url = _de(cliente_a, "editar")
    assert 'value="11.111.111-1"' in cliente_http_admin.get(url).content.decode()
    respuesta = cliente_http_admin.post(
        url, {"rut": "5.126.663-3", "nombre": "Nombre Corregido", "email": "nuevo@ejemplo.test"}
    )
    assert respuesta["Location"] == _usuarios(cliente_a.empresa)
    cliente_a.refresh_from_db()
    assert (cliente_a.rut, cliente_a.nombre, cliente_a.email) == (
        "51266633",
        "Nombre Corregido",
        "nuevo@ejemplo.test",
    )
    evento = EventoAuditoria.objects.get(accion=Accion.USUARIO_EDITADO)
    assert evento.detalle == "Cambió: RUT, nombre, correo" and evento.objeto_uuid == cliente_a.uuid

    # Guardar lo mismo no deja evento.
    cliente_http_admin.post(
        url, {"rut": "5.126.663-3", "nombre": "Nombre Corregido", "email": "nuevo@ejemplo.test"}
    )
    assert EventoAuditoria.objects.filter(accion=Accion.USUARIO_EDITADO).count() == 1

    # Cuenta ya activada: el campo sale deshabilitado y un RUT enviado a mano se ignora.
    url = _de(cliente_b_activo, "editar")
    pagina = cliente_http_admin.get(url).content.decode()
    assert re.search(r'<input type="text" name="rut"[^>]*disabled', pagina)
    cliente_http_admin.post(url, {"rut": "9.876.543-3", "nombre": "Otro Nombre", "email": ""})
    cliente_b_activo.refresh_from_db()
    assert cliente_b_activo.rut == "222222222" and cliente_b_activo.nombre == "Otro Nombre"


def test_editar_no_permite_tomar_el_rut_de_otra_cuenta(cliente_http_admin, cliente_a, cliente_b):
    respuesta = cliente_http_admin.post(
        _de(cliente_a, "editar"), {"rut": "22.222.222-2", "nombre": "X", "email": ""}
    )
    assert "Ya existe una cuenta con ese RUT." in respuesta.content.decode()
    cliente_a.refresh_from_db()
    assert cliente_a.rut == "111111111"


def test_desactivar_al_usuario_desde_el_panel_corta_su_sesion_y_revoca_sus_enlaces(
    cliente_http_admin, administrador_activo, cliente_a_activo, cliente_b_activo
):
    """Prueba 5 de la sección 12.2, para la cuenta: por el camino real del administrador."""
    de_a, de_b = Client(), Client()
    entrar(de_a, RUT_CLIENTE_A)
    entrar(de_b, cliente_b_activo.rut)
    sesiones = Session.objects.count()
    _, token = services.generar_enlace(cliente_a_activo, RESTABLECIMIENTO)
    url = _de(cliente_a_activo, "estado")
    assert cliente_http_admin.get(url).status_code == 405

    respuesta = cliente_http_admin.post(url, {"activo": "no"}, follow=True)
    contenido = respuesta.content.decode()
    assert "Se desactivó la cuenta de Cliente de A" in contenido and "Inactivo" in contenido
    cliente_a_activo.refresh_from_db()
    assert cliente_a_activo.is_active is False
    evento = EventoAuditoria.objects.get(accion=Accion.USUARIO_DESACTIVADO)
    assert evento.actor == administrador_activo and evento.objeto_uuid == cliente_a_activo.uuid

    assert de_a.get("/portal/")["Location"] == "/acceso/?next=/portal/"
    assert Session.objects.count() == sesiones - 1
    assert entrar(de_a, RUT_CLIENTE_A).status_code == 200
    assert de_b.get("/portal/").status_code == 200
    assert Client().get(f"/restablecer/{token}/").status_code == 404

    # Reactivar: el enlace anterior sigue sin servir, la sesión no revive, puede volver a entrar.
    cliente_http_admin.post(url, {"activo": "si"})
    assert EventoAuditoria.objects.filter(accion=Accion.USUARIO_REACTIVADO).count() == 1
    assert Client().get(f"/restablecer/{token}/").status_code == 404
    assert de_a.get("/portal/").status_code == 302
    assert entrar(de_a, RUT_CLIENTE_A)["Location"] == "/portal/"
    cliente_http_admin.post(url, {"activo": "si"})
    assert EventoAuditoria.objects.filter(accion=Accion.USUARIO_REACTIVADO).count() == 1


@pytest.mark.parametrize("accion", ["editar", "estado", "enlace", "desbloquear"])
def test_un_usuario_solo_se_alcanza_bajo_su_propia_empresa(
    cliente_http_admin, cliente_a_activo, empresa_b, administrador_activo, accion
):
    antes = EventoAuditoria.objects.count()
    base = f"/panel/clientes/{empresa_b.pk}/usuarios"
    for uuid in (cliente_a_activo.uuid, administrador_activo.uuid):
        respuesta = cliente_http_admin.post(f"{base}/{uuid}/{accion}/", {"activo": "no"})
        assert respuesta.status_code == 404
    cliente_a_activo.refresh_from_db()
    assert cliente_a_activo.is_active and not EnlaceAcceso.objects.exists()
    assert EventoAuditoria.objects.count() == antes
