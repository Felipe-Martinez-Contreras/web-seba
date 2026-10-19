"""Recorre todas las URL del proyecto (SEG-04, SEG-03; pruebas 1, 3 y 12 de la sección 12.2).

Solo lo que está en la lista pública explícita puede responder sin sesión. Una vista nueva
que no herede de un mixin de rol hace fallar esta prueba sin que nadie la agregue aquí.
"""

import datetime
import hashlib
import re
import uuid

import pytest
from django.conf import settings
from django.core import mail
from django.test import Client
from django.urls import URLPattern, URLResolver, get_resolver
from django.urls.resolvers import RegexPattern, RoutePattern

from auditoria.models import EventoAuditoria
from conftest import RUT_ADMINISTRADOR, RUT_CLIENTE_A, entrar, verificar_segundo_factor
from core.mixins import _VistaPrivada
from cuentas.models import EnlaceAcceso, Usuario
from documentos import almacenamiento, services
from documentos.models import Documento, VersionDocumento
from documentos.tests import archivos
from empresas.models import Carpeta, Empresa
from sitio.models import DatosNegocio, ImagenSitio, Rubro, Servicio, VarianteImagen
from sitio.tests import imagenes_prueba
from solicitudes.models import Solicitud

pytestmark = pytest.mark.django_db

# Nombres completos de las únicas vistas que responden a un visitante sin sesión.
PUBLICAS = {
    "core:salud",
    # Redirige al ícono, que es un archivo estático.
    "core:favicon",
    # Sitio público (PUB-01): páginas, sitemap y robots.
    "sitio:inicio",
    "sitio:servicios",
    "sitio:privacidad",
    "sitio:sitemap",
    "sitio:robots",
    # Imágenes subidas desde el panel, ya re-codificadas: las muestra el sitio público.
    "sitio:imagen",
    "solicitudes:contacto",
    "solicitudes:cotizacion",
    # Solo se muestra a quien acaba de enviar un formulario; a los demás los lleva al inicio.
    "solicitudes:recibida",
    "cuentas:acceso",
    "cuentas:recuperar",
    "cuentas:recuperar_enviado",
    # Sin un token válido responden 404; con él permiten definir la contraseña.
    "cuentas:activar",
    "cuentas:restablecer",
    # Solo admite POST; cerrar una sesión que no existe no hace nada.
    "cuentas:salir",
}

_VALORES = {
    "UUIDConverter": uuid.UUID("00000000-0000-4000-8000-000000000000"),
    "IntConverter": 1,
    "SlugConverter": "portada",
}


def _ruta_de(patron, reales):
    """Convierte el patrón en una ruta concreta. Cada parámetro toma el valor real que se
    haya entregado para su nombre y, si no hay, uno de relleno según su tipo."""
    if isinstance(patron, RoutePattern):

        def relleno(coincidencia):
            nombre = coincidencia.group(1)
            if nombre in reales:
                return str(reales[nombre])
            conversor = patron.converters[nombre]
            return str(_VALORES.get(type(conversor).__name__, "x"))

        return re.sub(r"<(?:\w+:)?(\w+)>", relleno, str(patron))
    assert isinstance(patron, RegexPattern)
    texto = str(patron)
    if texto == "(?P<url>.*)$":
        # Última ruta del admin de Django: atrapa cualquier dirección desconocida.
        return "direccion-inexistente/"
    aplicaciones = re.fullmatch(r"\^\(\?P<app_label>([\w|]+)\)/\$", texto)
    if aplicaciones:
        # Índice de una aplicación en el admin de Django.
        return aplicaciones.group(1).split("|")[0] + "/"
    raise AssertionError(f"Patrón con expresión regular no contemplado: {texto}")


def _recorrer(patrones, prefijo="", espacios=(), reales=None):
    reales = reales or {}
    for patron in patrones:
        if isinstance(patron, URLResolver):
            nuevos = (*espacios, patron.namespace) if patron.namespace else espacios
            yield from _recorrer(
                patron.url_patterns, prefijo + _ruta_de(patron.pattern, reales), nuevos, reales
            )
        else:
            assert isinstance(patron, URLPattern)
            nombre = ":".join((*espacios, patron.name or ""))
            yield nombre, "/" + prefijo + _ruta_de(patron.pattern, reales), patron.callback


# Rutas del panel que deben aparecer en el recorrido: si faltara alguna, las pruebas de
# abajo pasarían sin haberla probado.
PANEL = {
    "panel:inicio",
    "panel:clientes",
    "panel:cliente_nuevo",
    "panel:cliente",
    "panel:cliente_documentos",
    "panel:cliente_usuarios",
    "panel:cliente_actividad",
    "panel:cliente_editar",
    "panel:cliente_estado",
    "panel:carpeta_nueva",
    "panel:carpeta",
    "panel:documento_subir",
    "panel:cliente_papelera",
    "panel:documento",
    "panel:documento_editar",
    "panel:documento_mover",
    "panel:documento_reemplazar",
    "panel:documento_eliminar",
    "panel:documento_restaurar",
    "panel:version_ver",
    "panel:version_descargar",
    "panel:carpeta_editar",
    "panel:carpeta_mover",
    "panel:carpeta_eliminar",
    "panel:usuario_nuevo",
    "panel:usuario_editar",
    "panel:usuario_estado",
    "panel:usuario_enlace",
    "panel:usuario_desbloquear",
    "panel:auditoria",
    "panel:solicitudes_consultas",
    "panel:solicitudes_cotizaciones",
    "panel:solicitud",
    "panel:solicitud_estado",
    "panel:solicitud_notas",
    "panel:solicitud_reintentar",
    "panel:contenido",
    "panel:servicios",
    "panel:servicio_nuevo",
    "panel:servicio_editar",
    "panel:servicio_mover",
    "panel:servicio_estado",
    "panel:rubros",
    "panel:rubro_nuevo",
    "panel:rubro_editar",
    "panel:rubro_quitar_foto",
    "panel:rubro_mover",
    "panel:rubro_estado",
    "panel:rubro_eliminar",
    "panel:imagenes",
    "panel:imagen_cambiar",
    "panel:imagen_restaurar",
}

# Rutas del portal: todas de solo lectura. Una ruta nueva debe sumarse aquí o la prueba falla.
PORTAL = {
    "portal:inicio",
    "portal:carpetas",
    "portal:carpeta",
    "portal:buscar",
    "portal:documento",
    "portal:documento_ver",
    "portal:documento_descargar",
}


def _datos_post(carpeta=None):
    """Datos con los que un POST válido sí modificaría algo, si llegara a la vista: también
    un título, una carpeta de destino y archivos que la validación aceptaría."""
    datos = {
        "rut": "5.126.663-3",
        "razon_social": "Empresa creada por un intruso",
        "nombre": "Nombre puesto por un intruso",
        "email": "intruso@ejemplo.test",
        "carpetas_base": "on",
        "por_correo": "si",
        "activa": "no",
        "activo": "no",
        "direccion": "bajar",
        "titulo": "Título puesto por un intruso",
        "descripcion": "Descripción puesta por un intruso",
        "archivos": archivos.pdf("intruso.pdf"),
        "archivo": archivos.pdf("reemplazo-del-intruso.pdf"),
        "estado": "descartada",
        "notas_internas": "Notas puestas por un intruso",
        "icono": "flame",
        "resumen": "Resumen puesto por un intruso",
        "nombre_comercial": "Nombre comercial puesto por un intruso",
        "politica_privacidad": "Política puesta por un intruso",
        "portada-archivo": imagenes_prueba.subida("intruso.jpg", imagenes_prueba.jpg(800, 600)),
        "portada-alt": "Texto puesto por un intruso",
        "alt": "Texto alternativo puesto por un intruso",
    }
    if carpeta is not None:
        datos["carpeta"] = str(carpeta.pk)
    return datos


@pytest.fixture(scope="module")
def urls():
    encontradas = list(_recorrer(get_resolver().url_patterns))
    # Si el recorrido dejara de encontrar las URL, la prueba pasaría sin probar nada.
    nombres = {nombre for nombre, _, _ in encontradas}
    assert {"admin:index"} | PANEL | PORTAL <= nombres
    assert {nombre for nombre in nombres if nombre.startswith("portal:")} == PORTAL
    assert nombres >= PUBLICAS
    return encontradas


def _contenido_y_solicitud():
    """Un servicio, un rubro y una solicitud reales, para las rutas del panel que los
    identifican."""
    servicio, _ = Servicio.objects.get_or_create(
        slug="servicio-de-prueba", defaults={"nombre": "Servicio de prueba", "orden": 1}
    )
    Rubro.objects.get_or_create(nombre="Rubro de prueba", defaults={"orden": 1})
    solicitud = Solicitud.objects.first() or Solicitud.objects.create(
        tipo=Solicitud.Tipo.COTIZACION,
        nombre="Visitante de Prueba",
        email="visitante@ejemplo.test",
        telefono="+56 9 1234 5678",
        servicio=servicio,
        mensaje="Mensaje de prueba.",
        consentimiento=True,
        consentimiento_en=datetime.datetime(2026, 1, 15, tzinfo=datetime.UTC),
        notificacion=Solicitud.Notificacion.FALLIDA,
    )
    return servicio, solicitud


def _reales(empresa, usuario, carpeta, documento):
    servicio, solicitud = _contenido_y_solicitud()
    rubro = Rubro.objects.get(nombre="Rubro de prueba")
    return {
        "servicio": servicio.pk,
        "rubro": rubro.pk,
        "solicitud": solicitud.pk,
        "empresa": empresa.pk,
        "usuario": usuario.uuid,
        "carpeta": carpeta.pk,
        "documento": documento.pk,
        "version": documento.version_vigente_id,
        "ranura": "portada",
    }


def _rutas_del_panel(empresa, usuario, carpeta, documento):
    """Las rutas del panel con los identificadores reales de una empresa y de lo suyo."""
    reales = _reales(empresa, usuario, carpeta, documento)
    rutas = [
        (nombre, ruta)
        for nombre, ruta, _ in _recorrer(get_resolver().url_patterns, reales=reales)
        if nombre.startswith("panel:")
    ]
    assert {nombre for nombre, _ in rutas} == PANEL
    return rutas


def _rutas_del_portal(empresa, usuario, carpeta, documento):
    """Las rutas del portal con los identificadores reales de una empresa y de lo suyo."""
    reales = _reales(empresa, usuario, carpeta, documento)
    rutas = [
        (nombre, ruta)
        for nombre, ruta, _ in _recorrer(get_resolver().url_patterns, reales=reales)
        if nombre.startswith("portal:")
    ]
    assert {nombre for nombre, _ in rutas} == PORTAL
    return rutas


def _objetos_guardados():
    """Clave y SHA-256 de cada archivo del almacenamiento."""
    almacen = almacenamiento.almacen()
    guardados = {}
    for clave in almacen.claves():
        with almacen.abrir(clave) as archivo:
            guardados[clave] = hashlib.sha256(archivo.read()).hexdigest()
    return guardados


def _foto_de_la_base():
    """Todo lo que el panel puede modificar, para comprobar que un rechazo no cambió nada."""
    _contenido_y_solicitud()
    return {
        "empresas": list(Empresa.objects.order_by("rut").values()),
        "usuarios": list(Usuario.objects.order_by("rut").values()),
        "carpetas": list(Carpeta.objects.order_by("empresa", "orden", "nombre").values()),
        "documentos": list(Documento.objects.order_by("pk").values()),
        "versiones": list(VersionDocumento.objects.order_by("pk").values()),
        "servicios": list(Servicio.objects.order_by("pk").values()),
        "rubros": list(Rubro.objects.order_by("pk").values()),
        "solicitudes": list(Solicitud.objects.order_by("pk").values()),
        "datos_del_negocio": list(DatosNegocio.objects.values()),
        "imagenes": list(ImagenSitio.objects.order_by("pk").values()),
        "variantes": list(VarianteImagen.objects.order_by("pk").values()),
        "almacenamiento": _objetos_guardados(),
        "enlaces": EnlaceAcceso.objects.count(),
        "eventos": EventoAuditoria.objects.count(),
    }


def test_un_anonimo_solo_accede_a_la_lista_publica(urls):
    cliente = Client()
    for nombre, ruta, _ in urls:
        if nombre in PUBLICAS:
            continue
        respuesta = cliente.get(ruta)
        if respuesta.status_code == 302:
            destino = respuesta["Location"]
            # El admin de Django redirige dentro de sí mismo hasta su entrada, que lleva al acceso.
            assert destino.startswith(("/acceso/?next=", "/admin-tecnico/")), (nombre, destino)
        else:
            assert respuesta.status_code == 404, (nombre, ruta, respuesta.status_code)
    cadena = cliente.get("/admin-tecnico/", follow=True).redirect_chain
    assert cadena[-1][0].startswith("/acceso/?next=")


# Vistas privadas que no son clases: las pantallas del segundo factor. Las tres exigen la
# sesión de un administrador (`cuentas/tests/test_dos_factores.py`).
SEGUNDO_FACTOR = {"cuentas:verificacion", "cuentas:configurar_2fa", "cuentas:codigos_2fa"}


def test_toda_ruta_no_publica_pasa_por_un_control_de_rol(urls):
    """Un 404 con identificadores de relleno no prueba nada: una vista sin control que busque
    un objeto por su UUID también lo daría. Aquí se exige el control mismo."""
    for nombre, ruta, vista in urls:
        if nombre in PUBLICAS or nombre in SEGUNDO_FACTOR:
            continue
        if nombre.startswith("admin:"):
            # Todas las vistas del admin de Django salen de su sitio, que exige 2FA.
            continue
        clase = getattr(vista, "view_class", None)
        assert clase is not None and issubclass(clase, _VistaPrivada), (nombre, ruta)
        # El control es el `dispatch` del mixin: ninguna vista lo reemplaza.
        assert clase.dispatch is _VistaPrivada.dispatch, (nombre, ruta)
        assert clase.roles, (nombre, ruta)


def test_las_urls_publicas_responden_sin_sesion(urls):
    cliente = Client()
    esperado = {
        "core:favicon": 302,
        "cuentas:activar": 404,
        "cuentas:restablecer": 404,
        "cuentas:salir": 405,
        "solicitudes:recibida": 302,
        # Sin una imagen subida con ese SHA-256 no hay nada que entregar.
        "sitio:imagen": 404,
    }
    for nombre, ruta, _ in urls:
        if nombre in PUBLICAS:
            assert cliente.get(ruta).status_code == esperado.get(nombre, 200), nombre


def test_un_cliente_recibe_404_en_el_panel_y_en_el_admin(urls, cliente_a_activo):
    cliente = Client()
    entrar(cliente, RUT_CLIENTE_A)
    probadas = 0
    for nombre, ruta, _ in urls:
        if not nombre.startswith(("panel:", "admin:")):
            continue
        probadas += 1
        for metodo in (cliente.get, cliente.post):
            respuesta = metodo(ruta, follow=True)
            assert respuesta.status_code in (403, 404), (nombre, ruta, respuesta.status_code)
    assert probadas >= len(PANEL) + 3


@pytest.mark.parametrize("de_su_empresa", [True, False])
def test_un_cliente_recibe_404_en_el_panel_con_identificadores_reales_y_nada_cambia(
    de_su_empresa,
    cliente_a_activo,
    cliente_b_activo,
    carpeta_a,
    carpeta_b,
    documento_a,
    documento_b,
):
    """Pruebas 1 y 3 de la sección 12.2, con UUID que existen: el 404 es por el rol, no
    porque el objeto falte. Vale igual para su propia empresa que para una ajena.

    Solo lectura: un cliente no crea, edita, mueve, reemplaza, elimina ni restaura
    documentos con peticiones hechas a mano, y nada cambia en la base ni en el
    almacenamiento."""
    cliente = Client()
    entrar(cliente, RUT_CLIENTE_A)
    assert cliente.get("/portal/").status_code == 200
    rutas = (
        _rutas_del_panel(cliente_a_activo.empresa, cliente_a_activo, carpeta_a, documento_a)
        if de_su_empresa
        else _rutas_del_panel(cliente_b_activo.empresa, cliente_b_activo, carpeta_b, documento_b)
    )
    destino = Carpeta.objects.create(empresa=carpeta_a.empresa, nombre="Destino", orden=2)
    antes = _foto_de_la_base()
    assert len(antes["documentos"]) == 2 and len(antes["almacenamiento"]) == 2
    for nombre, ruta in rutas:
        assert cliente.get(ruta).status_code == 404, nombre
        assert cliente.post(ruta, _datos_post(destino)).status_code == 404, nombre
    assert _foto_de_la_base() == antes
    assert mail.outbox == []
    # El cliente sigue con su sesión: el rechazo no lo expulsa ni lo bloquea.
    assert cliente.get("/portal/").status_code == 200


def test_prueba_3_un_cliente_no_modifica_un_documento_en_la_papelera_ni_por_el_portal(
    cliente_a_activo, administrador, carpeta_a, documento_a
):
    """Restaurar exige un documento en la papelera: se prueba con uno que sí lo está.
    Ninguna ruta del portal admite un método que no sea GET (CLI-05)."""
    eliminado = services.subir(
        carpeta_a, archivos.pdf("eliminado.pdf"), actor=administrador, request=None
    )
    services.eliminar(eliminado, actor=administrador, request=None)
    cliente = Client()
    entrar(cliente, RUT_CLIENTE_A)
    antes = _foto_de_la_base()
    rutas = _rutas_del_panel(carpeta_a.empresa, cliente_a_activo, carpeta_a, eliminado)
    for nombre, ruta in rutas:
        assert cliente.post(ruta, _datos_post()).status_code == 404, nombre
    probadas = 0
    for documento in (documento_a, eliminado):
        for nombre, ruta in _rutas_del_portal(
            carpeta_a.empresa, cliente_a_activo, carpeta_a, documento
        ):
            probadas += 1
            assert cliente.post(ruta, _datos_post(carpeta_a)).status_code == 405, nombre
            for metodo in (cliente.put, cliente.patch, cliente.delete):
                assert metodo(ruta).status_code == 405, nombre
    assert probadas == 2 * len(PORTAL)
    assert _foto_de_la_base() == antes


def test_el_portal_con_identificadores_reales_solo_responde_al_cliente_de_esa_empresa(
    cliente_a_activo, cliente_b_activo, carpeta_a, documento_a, cliente_http_admin
):
    """Pruebas 1 y 2 sobre todas las rutas del portal, con UUID que existen: un anónimo va
    al acceso, y un administrador o un cliente de otra empresa reciben 404."""
    rutas = _rutas_del_portal(carpeta_a.empresa, cliente_a_activo, carpeta_a, documento_a)
    anonimo = Client()
    de_b = Client()
    de_b.force_login(cliente_b_activo)
    antes = _foto_de_la_base()
    for nombre, ruta in rutas:
        respuesta = anonimo.get(ruta)
        assert respuesta.status_code == 302, nombre
        assert respuesta["Location"] == f"/acceso/?next={ruta}", nombre
        assert cliente_http_admin.get(ruta).status_code == 404, nombre
        # Las rutas sin identificador muestran al cliente de B lo suyo; las demás, 404.
        esperado = 200 if nombre in {"portal:inicio", "portal:carpetas", "portal:buscar"} else 404
        assert de_b.get(ruta).status_code == esperado, nombre
    assert _foto_de_la_base() == antes
    # Su dueño sí las abre todas.
    de_a = Client()
    de_a.force_login(cliente_a_activo)
    for nombre, ruta in rutas:
        assert de_a.get(ruta).status_code == 200, nombre


def test_un_anonimo_es_enviado_al_acceso_con_identificadores_reales(
    cliente_b_activo, carpeta_b, documento_b
):
    cliente = Client()
    antes = _foto_de_la_base()
    for nombre, ruta in _rutas_del_panel(
        cliente_b_activo.empresa, cliente_b_activo, carpeta_b, documento_b
    ):
        for respuesta in (cliente.get(ruta), cliente.post(ruta, _datos_post())):
            assert respuesta.status_code == 302, nombre
            assert respuesta["Location"] == f"/acceso/?next={ruta}", nombre
    assert _foto_de_la_base() == antes


def test_un_administrador_sin_segundo_factor_no_usa_ninguna_ruta_del_panel(
    administrador_activo, totp, cliente_b_activo, carpeta_b, documento_b
):
    """Prueba 9 de la sección 12.2 sobre todas las rutas del panel: la contraseña sola no basta."""
    cliente = Client()
    entrar(cliente, RUT_ADMINISTRADOR)
    antes = _foto_de_la_base()
    for nombre, ruta in _rutas_del_panel(
        cliente_b_activo.empresa, cliente_b_activo, carpeta_b, documento_b
    ):
        for respuesta in (cliente.get(ruta), cliente.post(ruta, _datos_post())):
            assert respuesta.status_code == 302, nombre
            assert respuesta["Location"] == f"/acceso/verificacion/?next={ruta}", nombre
    assert _foto_de_la_base() == antes


def test_ninguna_ruta_del_panel_acepta_un_post_sin_token_csrf(
    administrador_activo, totp, cliente_b_activo, carpeta_b, documento_b
):
    """SEG-03 y prueba 12: ni siquiera un administrador verificado modifica algo sin el token."""
    admin = verificar_segundo_factor(Client(enforce_csrf_checks=True), administrador_activo, totp)
    assert admin.get("/panel/").status_code == 200
    antes = _foto_de_la_base()
    for nombre, ruta in _rutas_del_panel(
        cliente_b_activo.empresa, cliente_b_activo, carpeta_b, documento_b
    ):
        respuesta = admin.post(ruta, _datos_post())
        assert respuesta.status_code == 403, nombre
        assert "No pudimos procesar el formulario" in respuesta.content.decode(), nombre
    assert _foto_de_la_base() == antes


def test_un_administrador_recibe_404_en_el_portal(urls, cliente_http_admin):
    for nombre, ruta, _ in urls:
        if nombre.startswith("portal:"):
            assert cliente_http_admin.get(ruta).status_code == 404, nombre


def test_ninguna_vista_esta_exenta_de_csrf(urls):
    """SEG-03 y R5: ningún endpoint queda exento."""
    for nombre, ruta, vista in urls:
        assert not getattr(vista, "csrf_exempt", False), (nombre, ruta)


def test_un_formulario_sin_token_csrf_responde_403(cliente_a_activo, administrador_activo, totp):
    cliente = Client(enforce_csrf_checks=True)
    for ruta, datos in (
        ("/acceso/", {"rut": RUT_CLIENTE_A, "contrasena": "x"}),
        ("/recuperar/", {"rut": RUT_CLIENTE_A}),
        ("/salir/", {}),
        ("/activar/un-token-cualquiera/", {"new_password1": "x", "new_password2": "x"}),
    ):
        respuesta = cliente.post(ruta, datos)
        assert respuesta.status_code == 403, ruta
        assert "No pudimos procesar el formulario" in respuesta.content.decode(), ruta

    # También con sesión: tener la cookie de sesión no reemplaza al token.
    cliente.force_login(cliente_a_activo)
    assert cliente.post("/cuenta/", {"old_password": "x"}).status_code == 403
    assert cliente.post("/salir/").status_code == 403
    assert cliente.get("/portal/").status_code == 200

    admin = verificar_segundo_factor(Client(enforce_csrf_checks=True), administrador_activo, totp)
    url = (
        f"/panel/clientes/{cliente_a_activo.empresa_id}/usuarios/{cliente_a_activo.uuid}"
        "/desbloquear/"
    )
    assert admin.post(url).status_code == 403
    # Con el token en el encabezado, como lo envía la subida con progreso, la petición pasa.
    token = admin.get("/panel/").cookies["csrftoken"].value
    assert admin.post(url, HTTP_X_CSRFTOKEN=token).status_code == 302


def test_la_subida_con_progreso_envia_el_token_csrf_del_formulario():
    """Es el único envío por JavaScript: toma el token del propio formulario y lo manda en
    el encabezado. Ninguna página lo publica en otro atributo."""
    guion = (settings.BASE_DIR / "static" / "js" / "subida.js").read_text(encoding="utf-8")
    assert "formulario.querySelector('input[name=\"csrfmiddlewaretoken\"]')" in guion
    assert 'peticion.setRequestHeader("X-CSRFToken", token.value)' in guion


# --- HEAD (DEC-188) --------------------------------------------------------------------

# Rutas cuyo GET tiene efectos y que por eso no responden a HEAD. Las de entrega registran
# una vista o una descarga en la auditoría y firman una URL; la del enrolamiento crea el
# dispositivo TOTP pendiente; la de confirmación consume su mensaje de la sesión.
SIN_HEAD = {
    "portal:documento_ver",
    "portal:documento_descargar",
    "panel:version_ver",
    "panel:version_descargar",
    "cuentas:configurar_2fa",
    "solicitudes:recibida",
}


def _head_como_get(cliente, nombre, ruta):
    """HEAD responde lo mismo que GET, sin cuerpo; lo que no admite GET tampoco admite HEAD."""
    con_get = cliente.get(ruta)
    con_head = cliente.head(ruta)
    assert con_head.status_code == con_get.status_code, (nombre, ruta, con_head.status_code)
    assert con_head.content == b"", nombre
    assert con_head.get("Location") == con_get.get("Location"), nombre
    assert con_head.get("Content-Type") == con_get.get("Content-Type"), nombre
    return con_get.status_code


@pytest.mark.parametrize(
    "ruta",
    ["/", "/servicios/", "/contacto/", "/cotizacion/", "/privacidad/", "/salud/", "/acceso/"],
)
def test_head_responde_como_get_y_sin_cuerpo_en_las_rutas_publicas(client, negocio, ruta):
    assert client.get(ruta).content != b""
    assert _head_como_get(client, ruta, ruta) == 200
    # Los métodos que la ruta no admite siguen rechazados.
    assert client.put(ruta).status_code == 405
    assert client.delete(ruta).status_code == 405


@pytest.mark.parametrize("ruta", ["/portal/", "/panel/", "/cuenta/"])
def test_head_sin_sesion_en_una_ruta_privada_redirige_al_acceso_como_get(client, db, ruta):
    respuesta = client.head(ruta)
    assert respuesta.status_code == 302
    assert respuesta["Location"] == f"/acceso/?next={ruta}"
    assert respuesta["Location"] == client.get(ruta)["Location"]


def test_toda_ruta_que_acepta_get_responde_a_head_salvo_las_que_tienen_efectos(
    urls, cliente_a_activo, carpeta_a, documento_a, administrador_activo, totp
):
    """Guarda de DEC-188: una vista nueva que declare solo GET hace fallar esta prueba, salvo
    que su GET tenga efectos y se sume a `SIN_HEAD`."""
    assert {nombre for nombre, _, _ in urls} >= SIN_HEAD
    empresa = cliente_a_activo.empresa
    del_portal = Client()
    del_portal.force_login(cliente_a_activo)
    del_panel = verificar_segundo_factor(Client(), administrador_activo, totp)
    sin_segundo_factor = Client()
    sin_segundo_factor.force_login(administrador_activo)
    recorridos = [
        (Client(), [(nombre, ruta) for nombre, ruta, _ in urls]),
        (del_portal, _rutas_del_portal(empresa, cliente_a_activo, carpeta_a, documento_a)),
        (del_panel, _rutas_del_panel(empresa, cliente_a_activo, carpeta_a, documento_a)),
        # Las pantallas de la cuenta y del segundo factor, con y sin el segundo factor.
        (del_portal, [(n, r) for n, r, _ in urls if n.startswith("cuentas:")]),
        (del_panel, [(n, r) for n, r, _ in urls if n.startswith("cuentas:")]),
        (sin_segundo_factor, [(n, r) for n, r, _ in urls if n.startswith("cuentas:")]),
    ]
    con_get = set()
    for cliente, rutas in recorridos:
        for nombre, ruta in rutas:
            if nombre in SIN_HEAD:
                continue
            if _head_como_get(cliente, nombre, ruta) != 405:
                con_get.add(nombre)
    # El recorrido sí pasó por las páginas: no se limitó a comparar rechazos.
    assert {"sitio:inicio", "core:salud", "cuentas:acceso", "cuentas:mi_cuenta"} <= con_get
    assert {"portal:inicio", "portal:documento", "panel:inicio", "panel:cliente"} <= con_get
    # Lo que solo admite POST sigue rechazando HEAD.
    assert Client().head("/salir/").status_code == 405
    solo_post = f"/panel/clientes/{empresa.pk}/estado/"
    assert del_panel.head(solo_post).status_code == del_panel.get(solo_post).status_code == 405


def test_las_rutas_cuyo_get_tiene_efectos_rechazan_head_y_no_dejan_rastro(
    cliente_a_activo, carpeta_a, documento_a, administrador_activo, totp
):
    empresa = cliente_a_activo.empresa
    del_portal = Client()
    del_portal.force_login(cliente_a_activo)
    del_panel = verificar_segundo_factor(Client(), administrador_activo, totp)
    rutas = [
        (del_portal, nombre, ruta)
        for nombre, ruta in _rutas_del_portal(empresa, cliente_a_activo, carpeta_a, documento_a)
    ] + [
        (del_panel, nombre, ruta)
        for nombre, ruta in _rutas_del_panel(empresa, cliente_a_activo, carpeta_a, documento_a)
    ]
    rutas += [
        (del_panel, "cuentas:configurar_2fa", "/acceso/2fa/configurar/"),
        (Client(), "cuentas:configurar_2fa", "/acceso/2fa/configurar/"),
        (Client(), "solicitudes:recibida", "/solicitud-recibida/"),
    ]
    antes = _foto_de_la_base()
    probadas = set()
    for cliente, nombre, ruta in rutas:
        if nombre in SIN_HEAD:
            assert cliente.head(ruta).status_code == 405, nombre
            probadas.add(nombre)
    assert probadas == SIN_HEAD
    assert _foto_de_la_base() == antes
    # Con GET, las de entrega sí responden y dejan su evento.
    for nombre, ruta in _rutas_del_portal(empresa, cliente_a_activo, carpeta_a, documento_a):
        if nombre in SIN_HEAD:
            assert del_portal.get(ruta).status_code == 200, nombre
    assert EventoAuditoria.objects.count() == antes["eventos"] + 2


def test_head_en_un_enlace_de_activacion_no_lo_consume_ni_lo_marca(client, cliente_a):
    """Los filtros de correo visitan el enlace, con HEAD o con GET, antes que la persona."""
    from cuentas import services as cuentas

    enlace, token = cuentas.generar_enlace(cliente_a, EnlaceAcceso.Tipo.ACTIVACION)
    antes = (
        list(EnlaceAcceso.objects.values()),
        EventoAuditoria.objects.count(),
        list(Usuario.objects.filter(pk=cliente_a.pk).values()),
    )
    for _ in range(3):
        assert client.head(f"/activar/{token}/").status_code == 200
        assert client.get(f"/activar/{token}/").status_code == 200
    assert antes == (
        list(EnlaceAcceso.objects.values()),
        EventoAuditoria.objects.count(),
        list(Usuario.objects.filter(pk=cliente_a.pk).values()),
    )
    assert cuentas.enlace_vigente(EnlaceAcceso.Tipo.ACTIVACION, token) == enlace
