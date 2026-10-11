"""Almacenamiento privado y clave sin datos identificables (DOC-03; prueba 11 de la sección
12.2). Las pruebas de contrato corren contra el almacenamiento local y contra S3 emulado
con moto; el bucket real se comprueba con `comprobar_almacenamiento` (Etapa 8)."""

import hashlib
import io
import re
import uuid
from urllib.parse import parse_qs, urlsplit

import pytest
from django.core.checks import run_checks
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction

from conftest import RUT_ADMINISTRADOR, subir_documento
from core import rut as utilidades_rut
from documentos import almacenamiento, services
from documentos.models import VersionDocumento
from documentos.tests import archivos

pytestmark = pytest.mark.django_db

FORMA = re.compile(
    r"docs/[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
    r"/[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)


def _clave():
    return almacenamiento.clave_de(uuid.uuid4(), uuid.uuid4())


def _leer(almacen, clave):
    with almacen.abrir(clave) as archivo:
        return archivo.read()


def test_contrato_guardar_leer_listar_y_borrar(cualquier_almacen):
    almacen = cualquier_almacen
    clave = _clave()
    assert almacen.claves() == [] and not almacen.existe(clave)
    almacen.guardar(clave, io.BytesIO(archivos.BYTES_PDF), "application/pdf")
    assert almacen.existe(clave)
    assert almacen.claves() == [clave]
    assert _leer(almacen, clave) == archivos.BYTES_PDF
    almacen.borrar(clave)
    assert almacen.claves() == [] and not almacen.existe(clave)
    # Borrar lo que ya no existe no falla: la purga se puede reintentar.
    almacen.borrar(clave)


@pytest.mark.parametrize(
    "clave",
    [
        "docs/../../etc/passwd",
        "docs/76111111-6/informe.pdf",
        "/etc/passwd",
        "docs/00000000-0000-4000-8000-000000000000/00000000-0000-4000-8000-000000000000.pdf",
        "otra/00000000-0000-4000-8000-000000000000/00000000-0000-4000-8000-000000000000",
    ],
)
def test_ninguna_operacion_acepta_una_clave_con_otra_forma(cualquier_almacen, clave):
    for operacion in (
        lambda: cualquier_almacen.guardar(clave, io.BytesIO(b"x"), "application/pdf"),
        lambda: cualquier_almacen.abrir(clave),
        lambda: cualquier_almacen.existe(clave),
        lambda: cualquier_almacen.borrar(clave),
    ):
        with pytest.raises(almacenamiento.ClaveInvalida):
            operacion()
    assert cualquier_almacen.claves() == []


def test_prueba_11_la_clave_no_contiene_el_nombre_original_ni_el_rut(
    cualquier_almacen, carpeta_a, empresa_a, administrador
):
    nombre = "Matriz 76.111.111-6 Empresa A de Prueba SpA 12.345.678-5.pdf"
    documento = subir_documento(carpeta_a, administrador, archivos.pdf(nombre))
    version = documento.version_vigente
    clave = version.clave

    # 1. Forma exacta: docs/<uuid de la empresa>/<uuid de la versión>, ambos UUID4.
    assert FORMA.fullmatch(clave)
    assert clave == f"docs/{empresa_a.pk}/{version.pk}"
    assert version.pk.version == 4 and empresa_a.pk.version == 4

    # 2. Nada identificable: ni el nombre, ni la razón social, ni un RUT en ningún formato.
    ruts = [empresa_a.rut, utilidades_rut.normalizar(RUT_ADMINISTRADOR)]
    prohibidos = ["matriz", "empresa", "prueba", "spa", "pdf", "."]
    for rut in ruts:
        prohibidos += [rut, rut[:-1], utilidades_rut.formatear(rut)]
    for texto in prohibidos:
        assert texto.lower() not in clave.lower(), texto
    assert version.nombre_original == nombre  # el nombre vive en la base, no en la ruta

    # 3. El objeto existe en esa clave, con el SHA-256 y el tamaño registrados.
    contenido = _leer(cualquier_almacen, clave)
    assert hashlib.sha256(contenido).hexdigest() == version.sha256
    assert len(contenido) == version.tamano == len(archivos.BYTES_PDF)

    # 4. El almacenamiento completo solo tiene claves con esa forma.
    subir_documento(carpeta_a, administrador, archivos.ooxml("docx", "Nómina 11.111.111-1.docx"))
    claves = cualquier_almacen.claves()
    assert len(claves) == 2 and all(FORMA.fullmatch(c) for c in claves)


def test_en_s3_el_objeto_no_lleva_metadatos_con_el_nombre(almacen_s3, carpeta_a, administrador):
    documento = subir_documento(carpeta_a, administrador, archivos.pdf("Nómina de Juan Pérez.pdf"))
    objeto = almacen_s3._cliente.head_object(
        Bucket=almacen_s3.bucket, Key=documento.version_vigente.clave
    )
    assert objeto["Metadata"] == {}
    assert objeto["ContentType"] == "application/pdf"
    assert "ContentDisposition" not in objeto


@pytest.mark.parametrize(
    "clave",
    [
        "docs/76111111-6/Matriz de riesgos.pdf",
        "docs/00000000-0000-4000-8000-000000000000/informe.pdf",
        "00000000-0000-4000-8000-000000000000",
    ],
)
def test_la_base_rechaza_una_clave_con_otra_forma(documento_a, administrador, clave):
    vigente = documento_a.version_vigente
    with pytest.raises(IntegrityError), transaction.atomic():
        VersionDocumento.objects.create(
            documento=documento_a,
            numero=2,
            clave=clave,
            nombre_original="informe.pdf",
            tipo_mime="application/pdf",
            extension="pdf",
            tamano=vigente.tamano,
            sha256=vigente.sha256,
            subido_por=administrador,
        )


def test_la_url_firmada_dura_120_segundos_y_fija_tipo_y_disposicion(almacen_s3, settings):
    clave = _clave()
    almacen_s3.guardar(clave, io.BytesIO(archivos.BYTES_PDF), "application/pdf")
    disposicion = "attachment; filename*=utf-8''Se%C3%B1al%C3%A9tica.pdf"
    url = almacen_s3.url_firmada(
        clave,
        tipo_mime="application/pdf",
        disposicion=disposicion,
        segundos=almacenamiento.segundos_de_url(),
    )
    partes = urlsplit(url)
    consulta = parse_qs(partes.query)
    assert partes.path.endswith("/" + clave)
    assert consulta["X-Amz-Expires"] == ["120"]
    assert consulta["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"]
    assert len(consulta["X-Amz-Signature"][0]) == 64
    assert consulta["response-content-type"] == ["application/pdf"]
    assert consulta["response-content-disposition"] == [disposicion]
    # La clave secreta no viaja en la URL.
    assert settings.S3_SECRET_ACCESS_KEY not in url


@pytest.mark.parametrize(("configurado", "efectivo"), [(600, 120), (120, 120), (30, 30), (0, 1)])
def test_la_vigencia_de_la_url_nunca_supera_los_dos_minutos(settings, configurado, efectivo):
    settings.DESCARGA_URL_SEGUNDOS = configurado
    assert almacenamiento.segundos_de_url() == efectivo


def test_el_almacenamiento_local_no_ofrece_url(almacen_de_prueba):
    clave = _clave()
    almacen_de_prueba.guardar(clave, io.BytesIO(b"contenido"), "application/pdf")
    assert (
        almacen_de_prueba.url_firmada(
            clave, tipo_mime="application/pdf", disposicion="inline", segundos=120
        )
        is None
    )
    # Guardar no pisa un objeto existente ni deja temporales.
    with pytest.raises(FileExistsError):
        almacen_de_prueba.guardar(clave, io.BytesIO(b"otro"), "application/pdf")
    assert _leer(almacen_de_prueba, clave) == b"contenido"
    assert almacen_de_prueba.claves() == [clave]


def test_un_almacenamiento_desconocido_no_se_acepta(settings):
    settings.DOCUMENTOS_ALMACENAMIENTO = "ftp"
    with pytest.raises(ImproperlyConfigured):
        almacenamiento.almacen()
    assert [error.id for error in run_checks()] == ["documentos.E003"]


def test_las_comprobaciones_detectan_una_configuracion_insegura(settings):
    assert run_checks() == []
    settings.DOCUMENTOS_DIR = str(settings.BASE_DIR / "static" / "documentos")
    assert [error.id for error in run_checks()] == ["documentos.E001"]
    settings.DOCUMENTOS_ALMACENAMIENTO = "s3"
    settings.S3_BUCKET = settings.S3_ACCESS_KEY_ID = settings.S3_SECRET_ACCESS_KEY = ""
    assert [error.id for error in run_checks()] == ["documentos.E002"]
    settings.DOCUMENTOS_ALMACENAMIENTO = "local"
    settings.DOCUMENTOS_DIR = "/var/app/media"
    settings.DOCUMENTOS_FORMATOS = ["pdf", "svg"]
    settings.DOCUMENTOS_TAMANO_MAXIMO_MB = 0
    settings.PAPELERA_DIAS = 0
    assert [error.id for error in run_checks()] == [
        "documentos.E004",
        "documentos.E005",
        "documentos.E006",
    ]


def test_si_la_base_falla_el_objeto_guardado_se_borra(
    almacen_de_prueba, carpeta_a, administrador, monkeypatch
):
    def fallar(*args, **kwargs):
        raise RuntimeError("fallo simulado al registrar")

    monkeypatch.setattr(services, "registrar", fallar)
    with pytest.raises(RuntimeError):
        subir_documento(carpeta_a, administrador)
    assert almacen_de_prueba.claves() == []
    assert not VersionDocumento.objects.exists()


def test_comprobar_almacenamiento_recorre_el_local_y_no_deja_nada(almacen_de_prueba, capsys):
    call_command("comprobar_almacenamiento")
    salida = capsys.readouterr().out
    assert "Almacenamiento: local" in salida
    assert "URL firmada: no aplica" in salida
    assert "El almacenamiento funciona." in salida
    assert almacen_de_prueba.claves() == []


def test_comprobar_almacenamiento_falla_si_un_paso_no_se_cumple(almacen_de_prueba, monkeypatch):
    monkeypatch.setattr(type(almacen_de_prueba), "existe", lambda self, clave: False)
    with pytest.raises(CommandError, match="Falló: Guardar"):
        call_command("comprobar_almacenamiento")
    assert almacen_de_prueba.claves() == []


def test_comprobar_almacenamiento_exige_un_bucket_privado_y_una_url_de_dos_minutos(
    almacen_s3, monkeypatch, capsys
):
    """La descarga por HTTP se sustituye aquí (moto no atiende peticiones de red): lo que se
    prueba es qué exige el comando. Contra el bucket real se ejecuta sin sustitutos."""
    from documentos.management.commands import comprobar_almacenamiento as comando

    estado_sin_firma = 403
    pedidas = []

    def respuesta_simulada(url):
        pedidas.append(url)
        if "X-Amz-Signature" not in url:
            return estado_sin_firma, {}, b""
        consulta = parse_qs(urlsplit(url).query)
        encabezados = {
            "Content-Type": consulta["response-content-type"][0],
            "Content-Disposition": consulta["response-content-disposition"][0],
        }
        return 200, encabezados, comando._CONTENIDO

    monkeypatch.setattr(comando, "_estado", respuesta_simulada)
    call_command("comprobar_almacenamiento")
    salida = capsys.readouterr().out
    assert "Almacenamiento: s3" in salida
    assert "Sin firma no se puede leer (respondió 403): correcto" in salida
    assert "La URL vence en 120 segundos o menos: correcto" in salida
    assert len(pedidas) == 2 and "?" not in pedidas[1]
    assert almacen_s3.claves() == []

    # Un bucket público respondería 200 sin firma: el comando falla y limpia igual.
    estado_sin_firma = 200
    with pytest.raises(CommandError, match="Sin firma no se puede leer"):
        call_command("comprobar_almacenamiento")
    assert almacen_s3.claves() == []


def test_crear_bucket_es_solo_para_el_emulador_de_s3(almacen_s3, almacen_de_prueba, settings):
    # Con el bucket ya creado no falla; con el almacenamiento local, el comando lo rechaza.
    almacen_s3.crear_bucket()
    settings.S3_BUCKET = "otro-bucket"
    almacenamiento._almacen_s3.cache_clear()
    nuevo = almacenamiento.almacen()
    nuevo.crear_bucket()
    assert nuevo.claves() == []
    settings.DOCUMENTOS_ALMACENAMIENTO = "local"
    with pytest.raises(CommandError, match="solo aplica"):
        call_command("comprobar_almacenamiento", crear_bucket=True)


def test_comprobar_almacenamiento_con_firma_exige_que_el_bucket_valide_firma_y_vencimiento(
    almacen_s3, monkeypatch, capsys
):
    """Con --firma, para el bucket real. La red y la espera se sustituyen: lo que se prueba
    es que el comando falla ante un servicio que, como el emulador, no valida la firma."""
    from documentos.management.commands import comprobar_almacenamiento as comando

    esperas = []
    valida_firmas = True
    original = None

    def respuesta_simulada(url):
        nonlocal original
        consulta = parse_qs(urlsplit(url).query)
        if "X-Amz-Signature" not in consulta:
            return 403, {}, b""
        original = original or url
        if valida_firmas and (url != original or esperas):
            return 403, {}, b""  # firma alterada, o URL ya vencida
        encabezados = {
            "Content-Type": consulta["response-content-type"][0],
            "Content-Disposition": consulta["response-content-disposition"][0],
        }
        return 200, encabezados, comando._CONTENIDO

    monkeypatch.setattr(comando, "_estado", respuesta_simulada)
    monkeypatch.setattr(comando.time, "sleep", esperas.append)
    call_command("comprobar_almacenamiento", firma=True)
    salida = capsys.readouterr().out
    assert "Con la firma alterada no se puede leer (respondió 403): correcto" in salida
    assert "Vencida, la URL ya no sirve (respondió 403): correcto" in salida
    assert esperas == [130]

    valida_firmas, original, esperas[:] = False, None, []
    with pytest.raises(CommandError, match="Con la firma alterada no se puede leer"):
        call_command("comprobar_almacenamiento", firma=True)
    assert almacen_s3.claves() == []
