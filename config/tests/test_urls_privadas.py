"""Recorre todas las URL del proyecto (SEG-04, SEG-03; pruebas 1, 3 y 12 de la sección 12.2).

Solo lo que está en la lista pública explícita puede responder sin sesión. Una vista nueva
que no herede de un mixin de rol hace fallar esta prueba sin que nadie la agregue aquí.
"""

import hashlib
import re
import uuid

import pytest
from django.core import mail
from django.test import Client
from django.urls import URLPattern, URLResolver, get_resolver
from django.urls.resolvers import RegexPattern, RoutePattern

from auditoria.models import EventoAuditoria
from conftest import RUT_ADMINISTRADOR, RUT_CLIENTE_A, entrar, verificar_segundo_factor
from cuentas.models import EnlaceAcceso, Usuario
from documentos import almacenamiento, services
from documentos.models import Documento, VersionDocumento
from documentos.tests import archivos
from empresas.models import Carpeta, Empresa

pytestmark = pytest.mark.django_db

# Nombres completos de las únicas vistas que responden a un visitante sin sesión.
PUBLICAS = {
    "core:salud",
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
}

PORTAL_DOCUMENTOS = {"portal:documento_ver", "portal:documento_descargar"}


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
    }
    if carpeta is not None:
        datos["carpeta"] = str(carpeta.pk)
    return datos


@pytest.fixture(scope="module")
def urls():
    encontradas = list(_recorrer(get_resolver().url_patterns))
    # Si el recorrido dejara de encontrar las URL, la prueba pasaría sin probar nada.
    nombres = {nombre for nombre, _, _ in encontradas}
    assert {"portal:inicio", "admin:index"} | PANEL | PORTAL_DOCUMENTOS <= nombres
    assert nombres >= PUBLICAS
    return encontradas


def _reales(empresa, usuario, carpeta, documento):
    return {
        "empresa": empresa.pk,
        "usuario": usuario.uuid,
        "carpeta": carpeta.pk,
        "documento": documento.pk,
        "version": documento.version_vigente_id,
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
    return {
        "empresas": list(Empresa.objects.order_by("rut").values()),
        "usuarios": list(Usuario.objects.order_by("rut").values()),
        "carpetas": list(Carpeta.objects.order_by("empresa", "orden", "nombre").values()),
        "documentos": list(Documento.objects.order_by("pk").values()),
        "versiones": list(VersionDocumento.objects.order_by("pk").values()),
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


def test_las_urls_publicas_responden_sin_sesion(urls):
    cliente = Client()
    esperado = {"cuentas:activar": 404, "cuentas:restablecer": 404, "cuentas:salir": 405}
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
    """Restaurar exige un documento en la papelera: se prueba con uno que sí lo está. Las
    rutas de ver y descargar del portal no admiten ningún método que no sea GET."""
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
        reales = _reales(carpeta_a.empresa, cliente_a_activo, carpeta_a, documento)
        for nombre, ruta, _ in _recorrer(get_resolver().url_patterns, reales=reales):
            if nombre in PORTAL_DOCUMENTOS:
                probadas += 1
                assert cliente.post(ruta, _datos_post()).status_code == 405, nombre
                for metodo in (cliente.put, cliente.patch, cliente.delete):
                    assert metodo(ruta).status_code == 405, nombre
    assert probadas == 4
    assert _foto_de_la_base() == antes


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
    # Con el token en el encabezado, como lo envía HTMX, la petición pasa.
    token = admin.get("/panel/").cookies["csrftoken"].value
    assert admin.post(url, HTTP_X_CSRFTOKEN=token).status_code == 302


def test_las_plantillas_envian_el_token_csrf_en_el_encabezado_para_htmx(client):
    contenido = client.get("/acceso/").content.decode()
    assert 'hx-headers=\'{"X-CSRFToken": "' in contenido
