"""Gestión de documentos en el panel: ficha, edición, movimiento, reemplazo, papelera y purga
(ADM-08, ADM-09, DOC-07, DOC-08; escenarios E4 y E5 del lado del administrador)."""

import datetime

import pytest
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import Accion
from conftest import subir_documento
from documentos import services
from documentos.models import Documento, VersionDocumento
from documentos.querysets import SoloAgregar
from documentos.tests import archivos
from empresas.models import Carpeta

pytestmark = pytest.mark.django_db


def _de(documento, accion=""):
    base = f"/panel/clientes/{documento.empresa_id}/documentos/{documento.pk}/"
    return base + (f"{accion}/" if accion else "")


def _papelera(empresa):
    return f"/panel/clientes/{empresa.pk}/papelera/"


def _evento(accion):
    return EventoAuditoria.objects.get(accion=accion)


def test_la_ficha_muestra_datos_historial_y_acciones(
    cliente_http_admin, administrador_activo, documento_a, carpeta_a, empresa_a
):
    contenido = cliente_http_admin.get(_de(documento_a)).content.decode()
    vigente = documento_a.version_vigente
    assert "<h1" in contenido and "informe" in contenido and "informe.pdf" in contenido
    assert "Versión 1" in contenido and "Vigente" in contenido
    assert "Administradora de Prueba" in contenido
    # Migas: Clientes › empresa › carpeta › documento.
    assert f'href="/panel/clientes/{empresa_a.pk}/carpetas/{carpeta_a.pk}/"' in contenido
    base = f"/panel/clientes/{empresa_a.pk}/documentos/{documento_a.pk}/versiones/{vigente.pk}"
    assert f'href="{base}/descargar/"' in contenido
    # "Ver en pantalla" abre una pestaña nueva, sin visor incrustado.
    assert f'href="{base}/ver/" target="_blank" rel="noopener"' in contenido
    assert "<iframe" not in contenido and "<embed" not in contenido and "<object" not in contenido
    for accion in ("editar", "reemplazar", "eliminar"):
        assert _de(documento_a, accion) in contenido
    # Con una sola carpeta no hay adónde moverlo: la ficha lo explica en vez de ofrecerlo.
    assert _de(documento_a, "mover") not in contenido
    assert "Este cliente no tiene otra carpeta." in contenido


def test_un_documento_que_no_se_puede_ver_en_pantalla_solo_ofrece_descargar(
    cliente_http_admin, administrador_activo, carpeta_a
):
    documento = subir_documento(carpeta_a, administrador_activo, archivos.ooxml("docx"))
    contenido = cliente_http_admin.get(_de(documento)).content.decode()
    assert "/descargar/" in contenido and "/ver/" not in contenido


def test_editar_cambia_titulo_y_descripcion_y_queda_en_la_auditoria(
    cliente_http_admin, administrador_activo, documento_a
):
    url = _de(documento_a, "editar")
    assert 'value="informe"' in cliente_http_admin.get(url).content.decode()
    respuesta = cliente_http_admin.post(
        url, {"titulo": "  Informe   anual ", "descripcion": "Revisado en marzo"}
    )
    assert respuesta["Location"] == _de(documento_a)
    documento_a.refresh_from_db()
    assert (documento_a.titulo, documento_a.descripcion) == ("Informe anual", "Revisado en marzo")
    evento = _evento(Accion.DOCUMENTO_EDITADO)
    assert evento.actor == administrador_activo and evento.objeto_uuid == documento_a.pk
    assert evento.detalle == "informe → Informe anual"
    # Sin cambios no hay evento; un título vacío no se acepta.
    cliente_http_admin.post(url, {"titulo": "Informe anual", "descripcion": "Revisado en marzo"})
    assert EventoAuditoria.objects.filter(accion=Accion.DOCUMENTO_EDITADO).count() == 1
    respuesta = cliente_http_admin.post(url, {"titulo": "   ", "descripcion": ""})
    assert respuesta.status_code == 200
    documento_a.refresh_from_db()
    assert documento_a.titulo == "Informe anual"


def test_mover_solo_entre_carpetas_de_la_misma_empresa(
    cliente_http_admin, administrador_activo, documento_a, carpeta_a, carpeta_b, empresa_a
):
    """DOC-07."""
    otra = Carpeta.objects.create(empresa=empresa_a, nombre="Otra de A", orden=2)
    url = _de(documento_a, "mover")
    ficha = cliente_http_admin.get(_de(documento_a)).content.decode()
    assert f'value="{otra.pk}"' in ficha and f'value="{carpeta_b.pk}"' not in ficha

    # Con el UUID de una carpeta de otra empresa: se rechaza y nada cambia.
    respuesta = cliente_http_admin.post(url, {"carpeta": str(carpeta_b.pk)}, follow=True)
    assert "Seleccione una carpeta de destino de este cliente." in respuesta.content.decode()
    documento_a.refresh_from_db()
    assert documento_a.carpeta == carpeta_a and documento_a.empresa == empresa_a
    assert not EventoAuditoria.objects.filter(accion=Accion.DOCUMENTO_MOVIDO).exists()
    # El servicio tampoco lo permite, aunque se salte el formulario.
    with pytest.raises(services.OperacionNoPermitida):
        services.mover(documento_a, carpeta_b, actor=administrador_activo, request=None)

    respuesta = cliente_http_admin.post(url, {"carpeta": str(otra.pk)}, follow=True)
    assert "El documento se movió a la carpeta Otra de A." in respuesta.content.decode()
    documento_a.refresh_from_db()
    assert documento_a.carpeta == otra
    assert _evento(Accion.DOCUMENTO_MOVIDO).detalle == "informe: Carpeta de A → Otra de A"
    assert cliente_http_admin.get(url).status_code == 405


def test_e4_reemplazar_crea_una_version_nueva_y_conserva_la_anterior(
    cliente_http_admin, administrador_activo, documento_a, almacen_de_prueba
):
    """DOC-08 y E4, del lado del administrador."""
    primera = documento_a.version_vigente
    url = _de(documento_a, "reemplazar")
    nuevo = archivos.ooxml("docx", "Informe corregido.docx")
    respuesta = cliente_http_admin.post(url, {"archivo": nuevo}, follow=True)
    contenido = respuesta.content.decode()
    assert "Se subió la versión 2. Es la que ahora ve el cliente." in contenido
    documento_a.refresh_from_db()
    segunda = documento_a.version_vigente
    assert (segunda.numero, segunda.extension) == (2, "docx")
    assert list(documento_a.versiones.values_list("numero", flat=True)) == [2, 1]
    # Las dos están en el almacenamiento y en el historial.
    assert set(almacen_de_prueba.claves()) == {primera.clave, segunda.clave}
    assert "Versión 2" in contenido and "Versión 1" in contenido
    assert contenido.count("Vigente") == 1
    assert _evento(Accion.DOCUMENTO_REEMPLAZADO).detalle == "informe (versión 2)"

    # Un archivo inválido no crea versión ni deja un objeto suelto.
    malo = archivos.archivo("malo.pdf", archivos.BYTES_HTML)
    respuesta = cliente_http_admin.post(url, {"archivo": malo}, follow=True)
    assert "El archivo no se aceptó. El contenido no corresponde a un archivo PDF." in (
        respuesta.content.decode()
    )
    respuesta = cliente_http_admin.post(url, follow=True)
    assert "Seleccione el archivo que reemplazará al actual." in respuesta.content.decode()
    assert documento_a.versiones.count() == 2 and len(almacen_de_prueba.claves()) == 2


def test_las_versiones_no_se_editan_ni_se_borran(documento_a):
    version = documento_a.version_vigente
    version.nombre_original = "otro.pdf"
    with pytest.raises(SoloAgregar):
        version.save()
    with pytest.raises(SoloAgregar):
        version.delete()
    with pytest.raises(SoloAgregar):
        VersionDocumento.objects.update(nombre_original="otro.pdf")
    with pytest.raises(SoloAgregar):
        VersionDocumento.objects.all().delete()
    version.refresh_from_db()
    assert version.nombre_original == "informe.pdf"
    # La base tampoco admite dos versiones con el mismo número.
    with pytest.raises(IntegrityError), transaction.atomic():
        VersionDocumento.objects.create(
            documento=documento_a,
            numero=1,
            clave=version.clave.rsplit("/", 1)[0] + "/00000000-0000-4000-8000-000000000000",
            nombre_original="x.pdf",
            tipo_mime="application/pdf",
            extension="pdf",
            tamano=1,
            sha256=version.sha256,
            subido_por=version.subido_por,
        )
    with pytest.raises(ProtectedError):
        documento_a.delete()


def test_e5_eliminar_envia_a_la_papelera_y_restaurar_lo_devuelve(
    cliente_http_admin, administrador_activo, documento_a, carpeta_a, empresa_a, almacen_de_prueba
):
    assert "La papelera está vacía" in cliente_http_admin.get(_papelera(empresa_a)).content.decode()
    assert cliente_http_admin.get(_de(documento_a, "eliminar")).status_code == 405
    respuesta = cliente_http_admin.post(_de(documento_a, "eliminar"), follow=True)
    contenido = respuesta.content.decode()
    assert respuesta.redirect_chain == [
        (f"/panel/clientes/{empresa_a.pk}/carpetas/{carpeta_a.pk}/", 302)
    ]
    assert "se envió a la papelera" in contenido
    assert "Esta carpeta aún no tiene documentos" in contenido
    documento_a.refresh_from_db()
    assert documento_a.en_papelera and documento_a.eliminado_por == administrador_activo
    assert _evento(Accion.DOCUMENTO_ELIMINADO).objeto_uuid == documento_a.pk
    # El archivo sigue guardado: por eso se puede restaurar.
    assert almacen_de_prueba.existe(documento_a.version_vigente.clave)

    # En la papelera no tiene ficha ni admite cambios; solo restaurar.
    for accion in ("", "editar"):
        assert cliente_http_admin.get(_de(documento_a, accion)).status_code == 404
    for accion in ("mover", "reemplazar", "eliminar"):
        assert cliente_http_admin.post(_de(documento_a, accion)).status_code == 404
    with pytest.raises(services.OperacionNoPermitida):
        services.reemplazar(documento_a, archivos.pdf(), actor=administrador_activo, request=None)
    assert len(almacen_de_prueba.claves()) == 1  # el reemplazo rechazado no dejó un objeto

    papelera = cliente_http_admin.get(_papelera(empresa_a)).content.decode()
    assert "informe" in papelera and "Carpeta de A" in papelera
    assert "Se borrará definitivamente a partir del" in papelera
    assert _de(documento_a, "restaurar") in papelera
    documentos = cliente_http_admin.get(f"/panel/clientes/{empresa_a.pk}/documentos/")
    assert "Papelera (1)" in documentos.content.decode()

    respuesta = cliente_http_admin.post(_de(documento_a, "restaurar"), follow=True)
    assert "se restauró en la carpeta Carpeta de A" in respuesta.content.decode()
    documento_a.refresh_from_db()
    assert not documento_a.en_papelera and documento_a.eliminado_por is None
    assert _evento(Accion.DOCUMENTO_RESTAURADO).actor == administrador_activo
    # Restaurar algo que no está en la papelera no existe.
    assert cliente_http_admin.post(_de(documento_a, "restaurar")).status_code == 404


def test_pasado_el_plazo_ya_no_se_puede_restaurar(
    cliente_http_admin, administrador_activo, documento_a
):
    services.eliminar(documento_a, actor=administrador_activo, request=None)
    vencido = timezone.now() - datetime.timedelta(days=30, minutes=1)
    Documento.objects.filter(pk=documento_a.pk).update(eliminado_en=vencido)
    papelera = cliente_http_admin.get(_papelera(documento_a.empresa)).content.decode()
    assert "El plazo para restaurarlo ya venció" in papelera
    assert _de(documento_a, "restaurar") not in papelera
    respuesta = cliente_http_admin.post(_de(documento_a, "restaurar"), follow=True)
    assert "Pasaron más de 30 días desde que se eliminó" in respuesta.content.decode()
    documento_a.refresh_from_db()
    assert documento_a.en_papelera
    assert not EventoAuditoria.objects.filter(accion=Accion.DOCUMENTO_RESTAURADO).exists()
    documento_a.eliminado_en = None
    with pytest.raises(services.OperacionNoPermitida):
        services.restaurar(documento_a, actor=administrador_activo, request=None)


def test_purgar_papelera_borra_solo_lo_vencido_en_la_base_y_en_el_almacenamiento(
    administrador, documento_a, documento_b, carpeta_a, empresa_a, almacen_de_prueba, capsys
):
    """ADM-09."""
    vigente = subir_documento(carpeta_a, administrador, archivos.pdf("vigente.pdf"))
    services.reemplazar(
        documento_a, archivos.pdf("v2.pdf", b"% v2"), actor=administrador, request=None
    )
    claves_de_a = set(documento_a.versiones.values_list("clave", flat=True))
    for documento in (documento_a, documento_b):
        services.eliminar(documento, actor=administrador, request=None)
    ahora = timezone.now()
    Documento.objects.filter(pk=documento_a.pk).update(
        eliminado_en=ahora - datetime.timedelta(days=30, hours=1)
    )
    Documento.objects.filter(pk=documento_b.pk).update(
        eliminado_en=ahora - datetime.timedelta(days=29, hours=23)
    )
    antes = set(almacen_de_prueba.claves())
    assert len(antes) == 4 and claves_de_a < antes

    call_command("purgar_papelera")

    assert "Se borraron definitivamente 1 documentos" in capsys.readouterr().out
    assert set(Documento.objects.all()) == {documento_b, vigente}
    assert not VersionDocumento.objects.filter(documento_id=documento_a.pk).exists()
    assert set(almacen_de_prueba.claves()) == antes - claves_de_a
    evento = _evento(Accion.DOCUMENTO_PURGADO)
    assert evento.actor is None and evento.empresa == empresa_a
    assert evento.objeto_uuid == documento_a.pk and evento.detalle == "informe (2 versiones)"
    # Ejecutarlo de nuevo no borra nada más.
    call_command("purgar_papelera")
    assert Documento.objects.count() == 2 and len(almacen_de_prueba.claves()) == 2


def test_si_la_purga_falla_a_medias_la_siguiente_ejecucion_la_termina(
    administrador, documento_a, almacen_de_prueba, monkeypatch
):
    services.eliminar(documento_a, actor=administrador, request=None)
    Documento.objects.filter(pk=documento_a.pk).update(
        eliminado_en=timezone.now() - datetime.timedelta(days=40)
    )

    def fallar(*args, **kwargs):
        raise RuntimeError("fallo simulado al registrar")

    with monkeypatch.context() as parche:
        parche.setattr(services, "registrar", fallar)
        with pytest.raises(RuntimeError):
            services.purgar_vencidos()
    # El objeto ya se borró, pero la fila sigue: nada queda sin rastro.
    assert almacen_de_prueba.claves() == [] and Documento.objects.count() == 1
    assert services.purgar_vencidos() == 1
    assert not Documento.objects.exists() and not VersionDocumento.objects.exists()


def test_el_inicio_del_panel_cuenta_los_documentos_subidos_en_30_dias(
    cliente_http_admin, administrador_activo, documento_a, carpeta_a
):
    def indicador():
        contenido = cliente_http_admin.get("/panel/").content.decode()
        inicio = contenido.index("Documentos subidos en los últimos 30 días")
        return contenido[inicio : inicio + 200]

    assert ">1</p>" in indicador()
    # Un reemplazo también cuenta; lo que está en la papelera, no.
    services.reemplazar(
        documento_a, archivos.pdf("v2.pdf", b"% v2"), actor=administrador_activo, request=None
    )
    otro = subir_documento(carpeta_a, administrador_activo, archivos.pdf("otro.pdf"))
    assert ">3</p>" in indicador()
    services.eliminar(otro, actor=administrador_activo, request=None)
    assert ">2</p>" in indicador()


def test_un_titulo_con_html_se_muestra_escapado(
    cliente_http_admin, administrador_activo, carpeta_a
):
    documento = subir_documento(carpeta_a, administrador_activo)
    titulo = "<script>alert(1)</script>"
    cliente_http_admin.post(_de(documento, "editar"), {"titulo": titulo, "descripcion": titulo})
    documento.refresh_from_db()
    assert documento.titulo == titulo
    for url in (
        _de(documento),
        f"/panel/clientes/{documento.empresa_id}/carpetas/{carpeta_a.pk}/",
        f"/panel/clientes/{documento.empresa_id}/actividad/",
    ):
        contenido = cliente_http_admin.get(url).content.decode()
        assert "<script>alert" not in contenido, url
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in contenido, url
