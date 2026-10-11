"""Datos de demostración (sección 13). Todo lleva la marca DEMO y nada es contenido real.

Solo los usa el comando `cargar_demo`, que se niega a correr en producción.
"""

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction

from auditoria.services import Accion, registrar
from core import rut as utilidades_rut
from cuentas import services as cuentas
from cuentas.models import EnlaceAcceso, Usuario
from documentos import services as documentos
from empresas.models import Carpeta, Empresa
from sitio.models import DatosNegocio, Servicio
from sitio.pendientes import MARCADOR_DE_PRUEBA

EMPRESAS = (
    ("11.111.111-1", "Empresa Uno (DEMO)", "10000001", "Usuario Uno (DEMO)"),
    ("22.222.222-2", "Empresa Dos (DEMO)", "10000002", "Usuario Dos (DEMO)"),
)
DOCUMENTOS_POR_EMPRESA = 2

DATOS = {
    "nombre_comercial": "Nombre comercial (DEMO)",
    "titular": "Titular de la portada (DEMO)",
    "bajada": "Bajada de la portada, en una o dos líneas (DEMO).",
    "presentacion": "Presentación del negocio (DEMO).",
    "telefono": "+56 9 0000 0000 (DEMO)",
    "email_publico": "contacto@ejemplo.test",
    "ubicacion": "Comuna o región (DEMO)",
    "horario": "Horario de atención (DEMO)",
    "politica_privacidad": (
        f"{MARCADOR_DE_PRUEBA}\n\n"
        "Este texto existe solo para probar los formularios en desarrollo y en staging. "
        "No es la política de privacidad del negocio y no debe publicarse.\n\n"
        "El responsable del negocio debe reemplazarlo por el texto definitivo."
    ),
}
SERVICIOS = (
    ("Servicio uno (DEMO)", "shield-check"),
    ("Servicio dos (DEMO)", "clipboard-check"),
    ("Servicio tres (DEMO)", "hard-hat"),
    ("Servicio cuatro (DEMO)", "graduation-cap"),
)


def pdf_de_demo(texto):
    """Un PDF válido de una página con el texto indicado, generado sin dependencias."""
    contenido = f"BT /F1 20 Tf 72 720 Td ({texto}) Tj ET".encode("latin-1")
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(contenido), contenido),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    salida = bytearray(b"%PDF-1.4\n")
    posiciones = []
    for numero, objeto in enumerate(objetos, start=1):
        posiciones.append(len(salida))
        salida += b"%d 0 obj\n%s\nendobj\n" % (numero, objeto)
    inicio_xref = len(salida)
    salida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    for posicion in posiciones:
        salida += b"%010d 00000 n \n" % posicion
    salida += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objetos) + 1,
        inicio_xref,
    )
    return bytes(salida)


def cargar_contenido():
    """Completa solo lo que está vacío: nunca pisa un dato ya registrado. Devuelve qué creó."""
    creado = []
    datos = DatosNegocio.cargar()
    campos = [campo for campo, _ in DATOS.items() if not getattr(datos, campo)]
    for campo in campos:
        setattr(datos, campo, DATOS[campo])
    if campos:
        datos.save(update_fields=[*campos, "actualizado_en"])
        creado.append(f"Datos del negocio: {len(campos)} campos de prueba")
    if not Servicio.objects.exists():
        for orden, (nombre, icono) in enumerate(SERVICIOS, start=1):
            Servicio.objects.create(
                nombre=nombre,
                slug=f"servicio-demo-{orden}",
                icono=icono,
                resumen="Resumen del servicio (DEMO).",
                descripcion="Descripción del servicio (DEMO).",
                orden=orden,
            )
        creado.append(f"Servicios: {len(SERVICIOS)} de prueba")
    return creado


def cargar_empresas(administrador):
    """Crea las empresas de demostración que falten, con sus carpetas base, un usuario
    pendiente de activación y documentos PDF subidos a nombre del administrador. Devuelve
    pares (usuario, enlace de activación)."""
    enlaces = []
    for rut_empresa, razon_social, cuerpo, nombre in EMPRESAS:
        if Empresa.objects.filter(rut=utilidades_rut.normalizar(rut_empresa)).exists():
            continue
        rut_usuario = cuerpo + utilidades_rut.digito_verificador(cuerpo)
        with transaction.atomic():
            empresa = Empresa.objects.create(rut=rut_empresa, razon_social=razon_social)
            carpetas = Carpeta.objects.bulk_create(
                Carpeta(empresa=empresa, nombre=carpeta, orden=orden)
                for orden, carpeta in enumerate(settings.CARPETAS_BASE, start=1)
            )
            registrar(Accion.EMPRESA_CREADA, empresa=empresa, objeto=empresa, detalle="DEMO")
            usuario = Usuario.objects.create_user(
                rut_usuario, nombre=nombre, rol=Usuario.Rol.CLIENTE, empresa=empresa
            )
            registrar(Accion.USUARIO_CREADO, empresa=empresa, objeto=usuario, detalle="DEMO")
        for numero in range(1, DOCUMENTOS_POR_EMPRESA + 1):
            titulo = f"Documento {numero} DEMO"
            archivo = SimpleUploadedFile(
                f"{titulo}.pdf", pdf_de_demo(f"{titulo} - {razon_social}"), "application/pdf"
            )
            documentos.subir(carpetas[0], archivo, actor=administrador, request=None)
        _, token = cuentas.generar_enlace(usuario, EnlaceAcceso.Tipo.ACTIVACION)
        enlaces.append((usuario, cuentas.url_del_enlace(EnlaceAcceso.Tipo.ACTIVACION, token)))
    return enlaces
