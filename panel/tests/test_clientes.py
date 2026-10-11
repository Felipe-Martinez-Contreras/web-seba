"""Clientes en el panel: alta, listado, edición y estado (ADM-01 a ADM-05; E2 y E6)."""

import re

import pytest
from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.models import Session
from django.core import mail
from django.test import Client

from auditoria.models import EventoAuditoria
from auditoria.services import Accion
from conftest import RUT_CLIENTE_A, entrar
from cuentas import services as servicios_de_cuentas
from cuentas.models import EnlaceAcceso, Usuario
from empresas.models import Carpeta, Empresa

pytestmark = pytest.mark.django_db

CARPETAS_BASE = [
    "Matrices de riesgos",
    "Protocolos MINSAL",
    "Reglamento interno",
    "Formatos de inspección",
    "Documentos preventivos",
]
NUEVA = "tornillo-violeta-marea-88"


def _datos_de_empresa(**cambios):
    return {
        "rut": "77.333.333-5",
        "razon_social": "Constructora de Prueba SpA",
        "nombre_fantasia": "",
        "contacto_nombre": "",
        "contacto_email": "",
        "contacto_telefono": "",
        "notas_internas": "",
        "carpetas_base": "on",
        **cambios,
    }


def _enlace_de(contenido):
    """La URL que la página ofrece para copiar."""
    return re.search(r'id="enlace-de-acceso" type="text" value="([^"]+)"', contenido).group(1)


def test_e2_crear_cliente_con_carpetas_usuario_y_enlace_hasta_el_portal_vacio(
    cliente_http_admin, administrador_activo, settings
):
    """E2 de la sección 12.3, de punta a punta y sin correo configurado."""
    settings.MAILERS = {}

    # 1. El formulario ofrece las carpetas base, marcadas por defecto.
    formulario = cliente_http_admin.get("/panel/clientes/nuevo/").content.decode()
    assert re.search(r'<input type="checkbox" name="carpetas_base"[^>]*checked', formulario)
    assert "Matrices de riesgos, Protocolos MINSAL" in formulario

    # 2. Crear la empresa: queda con sus cinco carpetas y lleva a sus usuarios.
    respuesta = cliente_http_admin.post("/panel/clientes/nuevo/", _datos_de_empresa())
    empresa = Empresa.objects.get(rut="773333335")
    usuarios = f"/panel/clientes/{empresa.pk}/usuarios/"
    assert respuesta.status_code == 302 and respuesta["Location"] == usuarios
    assert empresa.activa and empresa.razon_social == "Constructora de Prueba SpA"
    assert list(empresa.carpetas.values_list("nombre", "orden")) == [
        (nombre, orden) for orden, nombre in enumerate(CARPETAS_BASE, start=1)
    ]
    alta = EventoAuditoria.objects.get(accion=Accion.EMPRESA_CREADA)
    assert alta.actor == administrador_activo and alta.empresa == empresa
    assert alta.objeto_uuid == empresa.pk and alta.detalle == "Con carpetas base"

    pagina = cliente_http_admin.get(usuarios).content.decode()
    assert "Se creó el cliente Constructora de Prueba SpA" in pagina
    assert "Este cliente aún no tiene usuarios" in pagina
    assert f'href="{usuarios}nuevo/"' in pagina

    # 3. Crear el usuario: sin correo configurado no se ofrece enviarlo.
    formulario = cliente_http_admin.get(f"{usuarios}nuevo/").content.decode()
    assert 'name="por_correo"' not in formulario
    assert "El correo no está configurado" in formulario

    respuesta = cliente_http_admin.post(
        f"{usuarios}nuevo/", {"rut": "5.126.663-3", "nombre": "Persona de Prueba", "email": ""}
    )
    assert respuesta.status_code == 200
    assert "no-store" in respuesta["Cache-Control"]
    usuario = Usuario.objects.get(rut="51266633")
    assert usuario.empresa == empresa and usuario.es_cliente and usuario.is_active
    assert not usuario.has_usable_password()
    creado = EventoAuditoria.objects.get(accion=Accion.USUARIO_CREADO)
    assert creado.actor == administrador_activo and creado.objeto_uuid == usuario.uuid

    # 4. La respuesta muestra el enlace, que no queda guardado en ninguna parte.
    contenido = respuesta.content.decode()
    assert "Enlace de activación" in contenido and "Se creó la cuenta" in contenido
    assert 'data-copia="enlace-de-acceso"' in contenido and "Copiar enlace" in contenido
    assert "Se puede usar una sola vez" in contenido
    assert "enviado" not in contenido.lower() and "se envió" not in contenido
    url = _enlace_de(contenido)
    assert url.startswith("http://testserver/activar/")
    token = url.removeprefix("http://testserver/activar/").rstrip("/")
    enlace = EnlaceAcceso.objects.get(usuario=usuario)
    assert enlace.tipo == EnlaceAcceso.Tipo.ACTIVACION and enlace.envio == ""
    assert enlace.creado_por == administrador_activo
    assert token not in enlace.token_hash
    assert token not in "".join(EventoAuditoria.objects.values_list("detalle", flat=True))
    assert token not in str(dict(cliente_http_admin.session))
    assert mail.outbox == []
    # La lista lo muestra como pendiente, con la vigencia del enlace.
    pagina = cliente_http_admin.get(usuarios).content.decode()
    assert "Pendiente" in pagina and "Enlace vigente hasta el" in pagina
    assert token not in pagina

    # 5. La persona define su contraseña y entra a su portal vacío.
    persona = Client()
    ruta = url.removeprefix("http://testserver")
    assert persona.get(ruta).status_code == 200
    respuesta = persona.post(ruta, {"new_password1": NUEVA, "new_password2": NUEVA})
    assert respuesta.status_code == 302 and respuesta["Location"] == "/portal/"
    portal = persona.get("/portal/").content.decode()
    assert "Hola, Constructora de Prueba SpA" in portal
    assert "Aún no hay documentos disponibles" in portal
    usuario.refresh_from_db()
    assert usuario.check_password(NUEVA)
    assert int(persona.session[SESSION_KEY]) == usuario.pk
    # El enlace no sirve dos veces, y la lista pasa a mostrarlo activo.
    assert Client().get(ruta).status_code == 404
    pagina = cliente_http_admin.get(usuarios).content.decode()
    assert "Activo" in pagina and "Pendiente" not in pagina


def test_sin_marcar_la_opcion_la_empresa_se_crea_sin_carpetas(cliente_http_admin):
    datos = _datos_de_empresa()
    del datos["carpetas_base"]
    assert cliente_http_admin.post("/panel/clientes/nuevo/", datos).status_code == 302
    assert Empresa.objects.get(rut="773333335").carpetas.count() == 0
    assert EventoAuditoria.objects.get(accion=Accion.EMPRESA_CREADA).detalle == "Sin carpetas base"


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"rut": "77.333.333-4"}, "Ingrese un RUT válido"),
        ({"rut": "76.111.111-6"}, "Ya existe un cliente con ese RUT."),
        ({"razon_social": ""}, "Este campo es obligatorio."),
        ({"contacto_email": "no-es-un-correo"}, "correo"),
    ],
)
def test_los_datos_invalidos_no_crean_nada_y_se_explican_por_campo(
    cliente_http_admin, empresa_a, cambios, mensaje
):
    respuesta = cliente_http_admin.post("/panel/clientes/nuevo/", _datos_de_empresa(**cambios))
    assert respuesta.status_code == 200
    contenido = respuesta.content.decode()
    assert mensaje in contenido
    assert "Revise los campos marcados" in contenido and 'aria-invalid="true"' in contenido
    # Lo escrito se conserva.
    assert 'value="Constructora de Prueba SpA"' in contenido or cambios.get("razon_social") == ""
    assert Empresa.objects.count() == 1 and Carpeta.objects.count() == 0
    assert not EventoAuditoria.objects.filter(accion=Accion.EMPRESA_CREADA).exists()


def test_el_listado_busca_por_rut_o_razon_social_y_filtra_por_estado(
    cliente_http_admin, empresa_a, empresa_b
):
    empresa_b.activa = False
    empresa_b.save()

    def nombres(consulta=""):
        contenido = cliente_http_admin.get("/panel/clientes/" + consulta).content.decode()
        return {e.razon_social for e in (empresa_a, empresa_b) if e.razon_social in contenido}

    ambas = {empresa_a.razon_social, empresa_b.razon_social}
    assert nombres() == ambas
    assert nombres("?q=76.111.111-6") == {empresa_a.razon_social}
    assert nombres("?q=761111116") == {empresa_a.razon_social}
    assert nombres("?q=76.222") == {empresa_b.razon_social}
    assert nombres("?q=empresa+b") == {empresa_b.razon_social}
    assert nombres("?q=prueba") == ambas
    assert nombres("?estado=activos") == {empresa_a.razon_social}
    assert nombres("?estado=inactivos") == {empresa_b.razon_social}
    assert nombres("?estado=inactivos&q=76.111") == set()

    sin_resultados = cliente_http_admin.get("/panel/clientes/?q=zzz").content.decode()
    assert "Sin resultados" in sin_resultados and "Quitar la búsqueda" in sin_resultados
    # El buscador superior conserva lo buscado y apunta solo a los clientes.
    assert 'action="/panel/clientes/"' in sin_resultados and 'value="zzz"' in sin_resultados


def test_el_listado_pagina_de_a_25_sin_consultas_por_fila(
    cliente_http_admin, django_assert_max_num_queries
):
    from core import rut

    Empresa.objects.bulk_create(
        Empresa(
            rut=f"{70_000_000 + n}{rut.digito_verificador(70_000_000 + n)}",
            razon_social=f"Empresa {n:02d}",
        )
        for n in range(30)
    )
    with django_assert_max_num_queries(12):
        primera = cliente_http_admin.get("/panel/clientes/").content.decode()
    assert primera.count('data-etiqueta="RUT"') == 25
    assert "Página 1 de 2" in primera
    segunda = cliente_http_admin.get("/panel/clientes/?page=2").content.decode()
    assert segunda.count('data-etiqueta="RUT"') == 5


def test_editar_guarda_los_cambios_y_audita_que_campos_cambiaron(
    cliente_http_admin, empresa_a, administrador_activo
):
    url = f"/panel/clientes/{empresa_a.pk}/editar/"
    pagina = cliente_http_admin.get(url).content.decode()
    assert 'value="76.111.111-6"' in pagina and "Crear las carpetas base" not in pagina

    datos = _datos_de_empresa(
        rut="76.111.111-6", razon_social="Empresa A Renombrada", notas_internas="Nota secreta"
    )
    respuesta = cliente_http_admin.post(url, datos)
    assert respuesta["Location"] == f"/panel/clientes/{empresa_a.pk}/documentos/"
    empresa_a.refresh_from_db()
    assert empresa_a.razon_social == "Empresa A Renombrada"
    assert empresa_a.notas_internas == "Nota secreta" and empresa_a.rut == "761111116"
    evento = EventoAuditoria.objects.get(accion=Accion.EMPRESA_EDITADA)
    assert evento.actor == administrador_activo and evento.empresa == empresa_a
    # Se anota qué cambió, nunca el contenido de las notas.
    assert evento.detalle == "Cambió: razón social, notas internas"

    # Guardar sin cambios no deja un evento falso.
    cliente_http_admin.post(url, datos)
    assert EventoAuditoria.objects.filter(accion=Accion.EMPRESA_EDITADA).count() == 1


def test_editar_no_permite_tomar_el_rut_de_otro_cliente(cliente_http_admin, empresa_a, empresa_b):
    respuesta = cliente_http_admin.post(
        f"/panel/clientes/{empresa_a.pk}/editar/", _datos_de_empresa(rut="76.222.222-1")
    )
    assert respuesta.status_code == 200
    contenido = respuesta.content.decode()
    assert "Ya existe un cliente con ese RUT." in contenido
    # Las migas siguen mostrando el nombre guardado, no el que se escribió.
    assert "Empresa A de Prueba SpA" in contenido
    empresa_a.refresh_from_db()
    assert empresa_a.rut == "761111116"


def test_e6_desactivar_la_empresa_desde_el_panel_corta_la_sesion_abierta(
    cliente_http_admin, administrador_activo, cliente_a_activo, cliente_b_activo, empresa_a
):
    """Prueba 5 de la sección 12.2 y E6, por el camino real del administrador."""
    de_a, de_b = Client(), Client()
    entrar(de_a, RUT_CLIENTE_A)
    entrar(de_b, cliente_b_activo.rut)
    assert de_a.get("/portal/").status_code == 200
    sesiones = Session.objects.count()
    _, token = servicios_de_cuentas.generar_enlace(cliente_a_activo, EnlaceAcceso.Tipo.ACTIVACION)

    # La ficha ofrece desactivar con un diálogo de confirmación que envía un POST.
    ficha = cliente_http_admin.get(f"/panel/clientes/{empresa_a.pk}/documentos/").content.decode()
    estado = f"/panel/clientes/{empresa_a.pk}/estado/"
    assert 'data-abre-dialogo="dialogo-estado-cliente"' in ficha
    assert f'<form method="post" action="{estado}">' in ficha
    assert '<input type="hidden" name="activa" value="no">' in ficha
    assert cliente_http_admin.get(estado).status_code == 405

    respuesta = cliente_http_admin.post(estado, {"activa": "no"}, follow=True)
    contenido = respuesta.content.decode()
    assert "El cliente quedó inactivo" in contenido and "Este cliente está inactivo" in contenido
    assert "Reactivar" in contenido
    empresa_a.refresh_from_db()
    assert empresa_a.activa is False
    evento = EventoAuditoria.objects.get(accion=Accion.EMPRESA_DESACTIVADA)
    assert evento.actor == administrador_activo and evento.objeto_uuid == empresa_a.pk

    # El cliente de A pierde el acceso en su petición siguiente y su sesión se elimina.
    respuesta = de_a.get("/portal/")
    assert respuesta.status_code == 302 and respuesta["Location"] == "/acceso/?next=/portal/"
    assert de_a.get("/cuenta/").status_code == 302
    assert Session.objects.count() == sesiones - 1
    # No puede volver a entrar ni usar un enlace pendiente; el de B no se entera.
    assert entrar(de_a, RUT_CLIENTE_A).status_code == 200
    assert Client().get(f"/activar/{token}/").status_code == 404
    assert de_b.get("/portal/").status_code == 200

    # Repetir la orden no duplica el evento.
    cliente_http_admin.post(estado, {"activa": "no"})
    assert EventoAuditoria.objects.filter(accion=Accion.EMPRESA_DESACTIVADA).count() == 1

    # Reactivar no revive la sesión anterior, pero permite entrar de nuevo.
    cliente_http_admin.post(estado, {"activa": "si"})
    empresa_a.refresh_from_db()
    assert empresa_a.activa is True
    assert EventoAuditoria.objects.filter(accion=Accion.EMPRESA_REACTIVADA).count() == 1
    assert de_a.get("/portal/").status_code == 302
    assert entrar(de_a, RUT_CLIENTE_A)["Location"] == "/portal/"


def test_la_ficha_tiene_tres_pestanas_con_url_propia(cliente_http_admin, empresa_a, carpeta_a):
    base = f"/panel/clientes/{empresa_a.pk}/"
    respuesta = cliente_http_admin.get(base)
    assert respuesta.status_code == 302 and respuesta["Location"] == base + "documentos/"
    for pestana, titulo in (
        ("documentos", "Carpetas"),
        ("usuarios", "Usuarios"),
        ("actividad", "Actividad"),
    ):
        contenido = cliente_http_admin.get(f"{base}{pestana}/").content.decode()
        assert f'class="pestana" href="{base}{pestana}/" aria-current="page"' in contenido
        assert contenido.count('aria-current="page"') >= 2
        assert titulo in contenido and "RUT: 76.111.111-6" in contenido
        assert 'aria-label="Migas de pan"' in contenido
    assert cliente_http_admin.get(f"{base}documentos/").content.decode().count("Carpeta de A") >= 1
    inexistente = "/panel/clientes/00000000-0000-4000-8000-000000000000/usuarios/"
    assert cliente_http_admin.get(inexistente).status_code == 404


def test_las_notas_internas_solo_aparecen_en_el_panel(
    cliente_http_admin, cliente_a_activo, empresa_a
):
    empresa_a.notas_internas = "Paga con atraso"
    empresa_a.save()
    ficha = cliente_http_admin.get(f"/panel/clientes/{empresa_a.pk}/documentos/").content.decode()
    assert "Paga con atraso" in ficha
    del_cliente = Client()
    entrar(del_cliente, RUT_CLIENTE_A)
    for ruta in ("/portal/", "/cuenta/"):
        assert "Paga con atraso" not in del_cliente.get(ruta).content.decode()


def test_un_nombre_con_script_se_muestra_escapado(cliente_http_admin):
    datos = _datos_de_empresa(
        razon_social="<script>alert(1)</script> SpA", notas_internas="<b>nota</b>\notra línea"
    )
    cliente_http_admin.post("/panel/clientes/nuevo/", datos)
    empresa = Empresa.objects.get(rut="773333335")
    for ruta in (
        "/panel/",
        "/panel/clientes/",
        f"/panel/clientes/{empresa.pk}/documentos/",
        f"/panel/clientes/{empresa.pk}/usuarios/",
        f"/panel/clientes/{empresa.pk}/actividad/",
        f"/panel/clientes/{empresa.pk}/editar/",
        "/panel/auditoria/",
    ):
        contenido = cliente_http_admin.get(ruta).content.decode()
        assert "<script>alert(1)" not in contenido, ruta
        assert "&lt;script&gt;alert(1)" in contenido, ruta
        assert "<b>nota</b>" not in contenido, ruta


def test_el_inicio_muestra_solo_datos_reales(cliente_http_admin, cliente_a, cliente_b_activo):
    """ADM-02: clientes activos, cuentas pendientes y clientes recientes, con los datos que
    existen. Las solicitudes tienen sus pruebas en test_solicitudes.py."""
    cliente_b_activo.empresa.activa = False
    cliente_b_activo.empresa.save()
    contenido = cliente_http_admin.get("/panel/").content.decode()
    indicador = re.search(r"Clientes activos</p>\s*<p[^>]*>(\d+)</p>", contenido)
    assert indicador and indicador.group(1) == "1"
    assert 'href="/panel/clientes/?estado=activos"' in contenido
    # cliente_a nunca definió su contraseña: aparece como pendiente, con enlace a sus usuarios.
    assert "Cuentas pendientes de activación" in contenido
    assert "1 cuenta pendiente" in contenido
    assert f'href="/panel/clientes/{cliente_a.empresa_id}/usuarios/"' in contenido
    assert "Clientes recientes" in contenido and "76.111.111-6" in contenido
    # Sin solicitudes, sus indicadores están en cero y la tabla lo dice.
    for etiqueta in ("Consultas pendientes", "Cotizaciones pendientes"):
        cifra = re.search(rf"{etiqueta}</p>\s*<p[^>]*>(\d+)</p>", contenido)
        assert cifra and cifra.group(1) == "0", etiqueta
    assert "Aún no hay solicitudes" in contenido

    # Sin pendientes, el aviso desaparece.
    cliente_a.set_password(NUEVA)
    cliente_a.save()
    assert "Cuentas pendientes" not in cliente_http_admin.get("/panel/").content.decode()


def test_el_inicio_sin_clientes_explica_como_empezar(cliente_http_admin):
    contenido = cliente_http_admin.get("/panel/").content.decode()
    assert "Aún no hay clientes" in contenido and 'href="/panel/clientes/nuevo/"' in contenido


def test_el_menu_del_panel_lista_solo_las_secciones_que_existen(cliente_http_admin):
    contenido = cliente_http_admin.get("/panel/clientes/").content.decode()
    menu = re.search(
        r'<nav class="hidden[^"]*" aria-label="Secciones">(.*?)</nav>', contenido, re.S
    )
    textos = re.findall(r"<span>([^<]+)</span>", menu.group(1))
    assert textos == [
        "Inicio",
        "Clientes",
        "Solicitudes",
        "Auditoría",
        "Configuración",
        "Contenido del sitio",
        "Mi cuenta",
        "Cerrar sesión",
    ]
    assert 'href="/panel/clientes/" aria-current="page"' in menu.group(1)
    assert 'content="noindex"' in contenido
