"""Datos de prueba compartidos: dos empresas (A y B), un cliente por empresa y un administrador."""

import time

import pytest
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from cuentas.models import Usuario
from empresas.models import Carpeta, Empresa
from sitio.models import DatosNegocio, Servicio

CLAVE = "caballo-bateria-grapa-2026"
RUT_CLIENTE_A = "11.111.111-1"
RUT_CLIENTE_B = "22.222.222-2"
RUT_ADMINISTRADOR = "12.345.678-5"
RUT_INEXISTENTE = "9.876.543-3"


@pytest.fixture
def empresa_a(db):
    return Empresa.objects.create(rut="76.111.111-6", razon_social="Empresa A de Prueba SpA")


@pytest.fixture
def empresa_b(db):
    return Empresa.objects.create(rut="76.222.222-1", razon_social="Empresa B de Prueba Ltda.")


@pytest.fixture
def carpeta_a(empresa_a):
    return Carpeta.objects.create(empresa=empresa_a, nombre="Carpeta de A", orden=1)


@pytest.fixture
def carpeta_b(empresa_b):
    return Carpeta.objects.create(empresa=empresa_b, nombre="Carpeta de B", orden=1)


@pytest.fixture
def cliente_a(empresa_a):
    return Usuario.objects.create_user(
        RUT_CLIENTE_A, nombre="Cliente de A", rol=Usuario.Rol.CLIENTE, empresa=empresa_a
    )


@pytest.fixture
def cliente_b(empresa_b):
    return Usuario.objects.create_user(
        RUT_CLIENTE_B, nombre="Cliente de B", rol=Usuario.Rol.CLIENTE, empresa=empresa_b
    )


@pytest.fixture
def administrador(db):
    return Usuario.objects.create_user(
        RUT_ADMINISTRADOR,
        nombre="Administradora de Prueba",
        email="admin@ejemplo.test",
        rol=Usuario.Rol.ADMINISTRADOR,
    )


def _con_clave(usuario):
    usuario.set_password(CLAVE)
    usuario.save()
    return usuario


@pytest.fixture
def cliente_a_activo(cliente_a):
    """Cliente de A con la contraseña CLAVE y correo registrado."""
    cliente_a.email = "cliente.a@ejemplo.test"
    return _con_clave(cliente_a)


@pytest.fixture
def cliente_b_activo(cliente_b):
    return _con_clave(cliente_b)


@pytest.fixture
def administrador_activo(administrador):
    """Administrador con la contraseña CLAVE y sin 2FA configurado."""
    return _con_clave(administrador)


@pytest.fixture
def totp(administrador_activo):
    """Dispositivo TOTP confirmado del administrador."""
    return TOTPDevice.objects.create(
        user=administrador_activo, name="Aplicación de autenticación", confirmed=True
    )


@pytest.fixture
def codigos_de_recuperacion(administrador_activo):
    dispositivo = StaticDevice.objects.create(
        user=administrador_activo, name="Códigos de recuperación"
    )
    codigos = ["aaaa1111", "bbbb2222"]
    StaticToken.objects.bulk_create(StaticToken(device=dispositivo, token=c) for c in codigos)
    return codigos


def codigo_totp(dispositivo, pasos=0):
    """El código que mostraría la aplicación ahora, o `pasos` intervalos más adelante."""
    generador = TOTP(
        dispositivo.bin_key, dispositivo.step, dispositivo.t0, dispositivo.digits, dispositivo.drift
    )
    generador.time = time.time() + pasos * dispositivo.step
    return f"{generador.token():0{dispositivo.digits}d}"


def entrar(cliente_http, rut, clave=CLAVE, **extra):
    """Envía el formulario de acceso."""
    return cliente_http.post("/acceso/", {"rut": rut, "contrasena": clave}, **extra)


def verificar_segundo_factor(cliente_http, administrador, dispositivo):
    """Deja al cliente HTTP con la sesión de un administrador que ya pasó el segundo factor."""
    cliente_http.force_login(administrador)
    sesion = cliente_http.session
    sesion[DEVICE_ID_SESSION_KEY] = dispositivo.persistent_id
    sesion.save()
    return cliente_http


@pytest.fixture
def cliente_http_admin(client, administrador_activo, totp):
    """Cliente HTTP con la sesión de un administrador que ya pasó el segundo factor."""
    return verificar_segundo_factor(client, administrador_activo, totp)


@pytest.fixture(autouse=True)
def almacen_de_prueba(settings, tmp_path):
    """Cada prueba guarda sus archivos en una carpeta temporal propia, con el backend local."""
    settings.DOCUMENTOS_ALMACENAMIENTO = "local"
    settings.DOCUMENTOS_DIR = str(tmp_path / "documentos")
    from documentos import almacenamiento

    return almacenamiento.almacen()


def subir_documento(carpeta, administrador, archivo=None):
    """Sube un PDF válido a la carpeta por el servicio real, como lo hace el panel."""
    from documentos import services
    from documentos.tests import archivos

    return services.subir(carpeta, archivo or archivos.pdf(), actor=administrador, request=None)


@pytest.fixture
def documento_a(carpeta_a, administrador):
    return subir_documento(carpeta_a, administrador)


@pytest.fixture
def documento_b(carpeta_b, administrador):
    return subir_documento(carpeta_b, administrador)


@pytest.fixture
def almacen_s3(settings):
    """Almacenamiento S3 contra moto, un emulador que corre dentro del proceso de pruebas:
    sin red y sin contenedor. No reemplaza la verificación contra un bucket real."""
    from moto import mock_aws

    from documentos import almacenamiento

    with mock_aws():
        settings.DOCUMENTOS_ALMACENAMIENTO = "s3"
        settings.S3_BUCKET = "documentos-de-prueba"
        settings.S3_ENDPOINT_URL = ""
        settings.S3_REGION = "us-east-1"
        settings.S3_ACCESS_KEY_ID = "clave-de-prueba"
        settings.S3_SECRET_ACCESS_KEY = "secreto-de-prueba"
        almacenamiento._almacen_s3.cache_clear()
        almacen = almacenamiento.almacen()
        almacen._cliente.create_bucket(Bucket=settings.S3_BUCKET)
        yield almacen
    almacenamiento._almacen_s3.cache_clear()


@pytest.fixture(params=["local", "s3"])
def cualquier_almacen(request, almacen_de_prueba):
    """La misma prueba contra los dos almacenamientos."""
    if request.param == "s3":
        return request.getfixturevalue("almacen_s3")
    return almacen_de_prueba


# --- Sitio público y solicitudes ------------------------------------------------------

POLITICA = "Política de privacidad de prueba.\n\nSegundo párrafo de la política."


@pytest.fixture
def negocio(db):
    """Datos del negocio completos, con política de privacidad: los formularios funcionan."""
    datos = DatosNegocio.cargar()
    datos.nombre_comercial = "Prevención de Prueba"
    datos.titular = "Titular de prueba"
    datos.bajada = "Bajada de prueba para la portada."
    datos.presentacion = "Presentación de prueba."
    datos.telefono = "+56 9 8765 4321"
    datos.email_publico = "contacto@prevencion-de-prueba.cl"
    datos.ubicacion = "Talca, Región del Maule"
    datos.horario = "Lunes a viernes, de 9:00 a 18:00"
    datos.politica_privacidad = POLITICA
    datos.save()
    return datos


@pytest.fixture
def servicio(db):
    return Servicio.objects.create(
        nombre="Servicio de prueba",
        slug="servicio-de-prueba",
        icono="hard-hat",
        resumen="Resumen de prueba.",
        descripcion="Descripción de prueba.",
        orden=1,
    )


def marca_de_hace(segundos):
    """Marca de tiempo del antispam emitida hace `segundos`, como la de un formulario que
    lleva ese tiempo abierto."""
    from solicitudes import antispam

    return antispam._firmante.sign(str(int(time.time() - segundos)))


def datos_de_consulta(**cambios):
    return {
        "nombre": "Visitante de Prueba",
        "email": "visitante@ejemplo.test",
        "telefono": "",
        "mensaje": "Necesito información sobre sus servicios.",
        "consentimiento": "on",
        "sitio_web": "",
        "marca": marca_de_hace(30),
        **cambios,
    }


def datos_de_cotizacion(**cambios):
    return datos_de_consulta(
        **{
            "telefono": "+56 9 1234 5678",
            "empresa": "Constructora de Prueba Ltda.",
            "servicio": "servicio-de-prueba",
            "trabajadores": "11-25",
            "comuna": "Talca",
            **cambios,
        }
    )
