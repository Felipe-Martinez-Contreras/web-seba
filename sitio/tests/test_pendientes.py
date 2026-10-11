"""Contenido pendiente (PUB-06) y datos de demostración (sección 13)."""

import io

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from cuentas.models import Usuario
from documentos.models import Documento
from empresas.models import Empresa
from sitio import pendientes, services
from sitio.models import DatosNegocio, Servicio

pytestmark = pytest.mark.django_db


def _contenido_pendiente(*argumentos):
    salida = io.StringIO()
    call_command("contenido_pendiente", *argumentos, stdout=salida)
    return salida.getvalue()


def _cargar_demo():
    salida = io.StringIO()
    call_command("cargar_demo", stdout=salida)
    return salida.getvalue()


def test_la_migracion_crea_el_registro_unico_vacio_y_la_base_no_admite_otro():
    from django.db import IntegrityError, transaction

    datos = DatosNegocio.objects.get()
    assert datos.pk == 1 and datos.nombre_comercial == "" and datos.politica_privacidad == ""
    with pytest.raises(IntegrityError), transaction.atomic():
        DatosNegocio.objects.create(pk=2)
    assert DatosNegocio.cargar() == datos


@pytest.mark.parametrize(
    ("valor", "falta", "de_prueba"),
    [
        ("", True, False),
        ("   ", True, False),
        (None, True, False),
        ("[COMPLETAR]", True, False),
        ("Teléfono [COMPLETAR]", True, False),
        ("Texto definitivo", False, False),
        ("TEXTO DE PRUEBA\n\nPolítica", False, True),
        ("Titular (DEMO)", False, True),
        ("contacto@ejemplo.test", False, True),
    ],
)
def test_la_regla_distingue_lo_que_falta_de_lo_que_es_de_prueba(valor, falta, de_prueba):
    assert pendientes.falta(valor) is falta
    assert pendientes.de_prueba(valor) is de_prueba
    assert pendientes.disponible(valor) == ("" if falta else valor.strip())


def test_pub_06_con_todo_en_completar_el_comando_lista_cada_marcador(settings):
    """El estado actual del proyecto: los datos de la sección 0 siguen en [COMPLETAR]."""
    settings.NOTIFICACIONES_DESTINATARIOS = []
    settings.MAILERS = {}
    salida = _contenido_pendiente()
    assert "Contenido pendiente [COMPLETAR]: 12" in salida
    for dato in (
        "Nombre comercial: Sin completar",
        "Titular de la portada: Sin completar",
        "Bajada de la portada: Sin completar",
        "Presentación: Sin completar",
        "Teléfono: Sin completar",
        "Correo público: Sin completar",
        "Comuna o región: Sin completar",
        "Horario de atención: Sin completar",
        "Texto de la política: Sin texto: los formularios públicos están ocultos "
        "(bloquea los formularios)",
        "Servicios ofrecidos: No hay ningún servicio activo",
        "Correo saliente: Sin configurar",
        "Correo que recibe las notificaciones: Sin destinatarios",
    ):
        assert dato in salida, dato
    assert "Panel › Configuración › Contenido del sitio" in salida
    assert "Variable de entorno NOTIFICACIONES_DESTINATARIOS" in salida
    # WhatsApp y las redes sociales son opcionales: no figuran.
    for opcional in ("WhatsApp", "Instagram", "LinkedIn", "Facebook"):
        assert opcional not in salida, opcional


def test_pub_06_el_comando_termina_bien_salvo_con_estricto():
    assert "Contenido pendiente" in _contenido_pendiente()
    with pytest.raises(CommandError, match="Quedan 10 pendientes"):
        _contenido_pendiente("--estricto")


def test_pub_06_con_todo_completo_no_queda_nada_pendiente(negocio, servicio):
    assert services.contenido_pendiente() == []
    assert "No hay contenido pendiente." in _contenido_pendiente("--estricto")


def test_pub_06_un_servicio_activo_incompleto_o_un_marcador_en_un_dato_siguen_pendientes(
    negocio, servicio
):
    servicio.resumen = ""
    servicio.descripcion = "[COMPLETAR]"
    servicio.save()
    Servicio.objects.create(nombre="Inactivo y vacío", slug="inactivo", orden=2, activo=False)
    negocio.horario = "[COMPLETAR]"
    negocio.save()
    listado = {(p.grupo, p.nombre): p for p in services.contenido_pendiente()}
    assert listado[("Servicios", "Servicio de prueba")].detalle == "Falta: resumen, descripción"
    assert listado[("Datos del negocio", "Horario de atención")].detalle == "Sin completar"
    assert (
        listado[("Servicios", "Servicio de prueba")].url
        == f"/panel/contenido/servicios/{servicio.pk}/editar/"
    )
    # Un servicio inactivo no se publica: no hay nada que completar en él.
    assert len(listado) == 2


def test_pub_06_el_inicio_del_panel_muestra_el_mismo_aviso(cliente_http_admin, negocio, servicio):
    contenido = cliente_http_admin.get("/panel/").content.decode()
    assert "Contenido pendiente" not in contenido
    negocio.titular = ""
    negocio.politica_privacidad = ""
    negocio.save()
    contenido = cliente_http_admin.get("/panel/").content.decode()
    assert "Contenido pendiente [COMPLETAR]: 2" in contenido
    assert 'href="/panel/contenido/">Contenido del sitio</a>' in contenido
    assert len(services.contenido_pendiente()) == 2


# --- cargar_demo -----------------------------------------------------------------------


def test_cargar_demo_se_niega_a_correr_en_produccion(administrador, settings):
    assert settings.DEBUG is False and settings.DEMO_PERMITIDO is False
    with pytest.raises(CommandError, match="no se ejecuta en producción"):
        _cargar_demo()
    assert not Empresa.objects.exists() and not Servicio.objects.exists()
    assert DatosNegocio.objects.get().politica_privacidad == ""


def test_cargar_demo_necesita_un_administrador(settings):
    settings.DEMO_PERMITIDO = True
    with pytest.raises(CommandError, match="crear_administrador"):
        _cargar_demo()


def test_cargar_demo_carga_todo_marcado_como_demo_y_la_politica_de_prueba(
    administrador, settings, client
):
    settings.DEMO_PERMITIDO = True
    salida = _cargar_demo()

    datos = DatosNegocio.objects.get()
    assert datos.politica_privacidad.startswith("TEXTO DE PRUEBA")
    assert "(DEMO)" in datos.nombre_comercial and "(DEMO)" in datos.titular
    assert Servicio.objects.count() == 4
    assert all("(DEMO)" in servicio.nombre for servicio in Servicio.objects.all())

    empresas = list(Empresa.objects.order_by("rut"))
    assert [empresa.rut for empresa in empresas] == ["111111111", "222222222"]
    assert all("(DEMO)" in empresa.razon_social for empresa in empresas)
    for empresa in empresas:
        assert empresa.carpetas.count() == len(settings.CARPETAS_BASE)
        usuario = empresa.usuarios.get()
        assert usuario.rol == Usuario.Rol.CLIENTE and not usuario.has_usable_password()
        assert "(DEMO)" in usuario.nombre
        documentos = Documento.objects.filter(empresa=empresa)
        assert documentos.count() == 2 and all("DEMO" in d.titulo for d in documentos)
        assert all(d.version_vigente.tipo_mime == "application/pdf" for d in documentos)
    assert salida.count("Enlace de activación (un solo uso): http://testserver/activar/") == 2

    # Con la política de prueba los formularios funcionan, pero todo sigue pendiente.
    assert "<form" in client.get("/contacto/").content.decode()
    assert "TEXTO DE PRUEBA" in client.get("/privacidad/").content.decode()
    detalles = {p.nombre: p.detalle for p in services.contenido_pendiente()}
    assert detalles["Texto de la política"] == pendientes.ES_DE_PRUEBA
    assert detalles["Nombre comercial"] == pendientes.ES_DE_PRUEBA
    assert detalles["Correo público"] == pendientes.ES_DE_PRUEBA
    assert detalles["Servicio uno (DEMO)"] == pendientes.ES_DE_PRUEBA
    with pytest.raises(CommandError):
        _contenido_pendiente("--estricto")


def test_cargar_demo_no_pisa_datos_reales_ni_duplica_al_repetirse(
    administrador, negocio, servicio, settings
):
    settings.DEMO_PERMITIDO = True
    _cargar_demo()
    datos = DatosNegocio.objects.get()
    assert datos.nombre_comercial == "Prevención de Prueba"
    assert datos.politica_privacidad.startswith("Política de privacidad de prueba.")
    assert list(Servicio.objects.values_list("nombre", flat=True)) == ["Servicio de prueba"]
    assert Empresa.objects.count() == 2

    assert "ya estaban cargados" in _cargar_demo()
    assert Empresa.objects.count() == 2 and Documento.objects.count() == 4


def test_el_pdf_de_demostracion_pasa_la_validacion_de_documentos():
    from django.core.files.uploadedfile import SimpleUploadedFile

    from documentos import validacion
    from sitio.demo import pdf_de_demo

    datos = pdf_de_demo("Documento 1 DEMO")
    assert datos.startswith(b"%PDF-1.4") and datos.rstrip().endswith(b"%%EOF")
    # La tabla de referencias apunta al inicio real de cada objeto.
    inicio = int(datos.split(b"startxref\n")[1].split(b"\n")[0])
    assert datos[inicio:].startswith(b"xref")
    validado = validacion.validar(SimpleUploadedFile("demo.pdf", datos))
    assert validado.tipo_mime == "application/pdf"


def test_cargar_demo_no_acepta_debug_como_permiso(administrador, settings):
    """`manage.py` usa la configuración de desarrollo si falta la variable de entorno: en el
    servidor, DEBUG no puede ser lo que autorice a cargar datos de demostración."""
    settings.DEBUG = True
    assert settings.DEMO_PERMITIDO is False
    with pytest.raises(CommandError, match="DEMO_PERMITIDO"):
        _cargar_demo()
    assert Empresa.objects.count() == 0
