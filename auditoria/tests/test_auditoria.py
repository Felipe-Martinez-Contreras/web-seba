import pytest

from auditoria.models import EventoAuditoria, SoloAgregar
from auditoria.services import Accion, registrar


def test_registrar_guarda_actor_empresa_objeto_e_ip(cliente_a, rf):
    request = rf.get("/")
    request.ip_cliente = "203.0.113.7"
    evento = registrar(Accion.ACCESO_EXITOSO, request=request, actor=cliente_a, objeto=cliente_a)
    evento.refresh_from_db()
    assert evento.actor == cliente_a
    assert evento.empresa == cliente_a.empresa
    assert evento.objeto_tipo == "usuario"
    assert evento.objeto_uuid == cliente_a.uuid
    assert evento.ip == "203.0.113.7"
    assert evento.fecha is not None


def test_el_objeto_puede_tener_el_uuid_como_clave_primaria(empresa_a):
    evento = registrar(Accion.DESBLOQUEO, objeto=empresa_a)
    assert evento.objeto_tipo == "empresa"
    assert evento.objeto_uuid == empresa_a.pk


@pytest.mark.django_db
def test_el_rut_intentado_se_guarda_normalizado_solo_si_es_un_rut_valido():
    assert registrar(Accion.ACCESO_FALLIDO, rut_intentado="12.345.678-5").rut_intentado == (
        "123456785"
    )
    # Alguien pudo escribir su contraseña en el campo del RUT: no se guarda.
    assert registrar(Accion.ACCESO_FALLIDO, rut_intentado="MiClaveSecreta1").rut_intentado == ""
    assert registrar(Accion.ACCESO_FALLIDO, rut_intentado="12.345.678-9").rut_intentado == ""


@pytest.mark.django_db
def test_los_eventos_no_se_editan_ni_se_borran():
    evento = registrar(Accion.BLOQUEO, detalle="original")
    evento.detalle = "alterado"
    with pytest.raises(SoloAgregar):
        evento.save()
    with pytest.raises(SoloAgregar):
        evento.delete()
    with pytest.raises(SoloAgregar):
        EventoAuditoria.objects.filter(pk=evento.pk).update(detalle="alterado")
    with pytest.raises(SoloAgregar):
        EventoAuditoria.objects.all().delete()
    evento.refresh_from_db()
    assert evento.detalle == "original"


@pytest.mark.django_db
def test_el_detalle_se_recorta():
    assert len(registrar(Accion.BLOQUEO, detalle="x" * 500).detalle) == 200
