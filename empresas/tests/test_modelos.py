import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction

from empresas.models import Empresa


def test_la_empresa_se_identifica_con_uuid(empresa_a):
    assert isinstance(empresa_a.pk, uuid.UUID)
    assert empresa_a.activa is True
    assert empresa_a.creado_en is not None
    assert empresa_a.actualizado_en is not None


def test_el_rut_se_guarda_normalizado_y_se_busca_en_cualquier_formato(empresa_a):
    with connection.cursor() as cursor:
        cursor.execute("SELECT rut FROM empresas_empresa WHERE id = %s", [empresa_a.pk])
        assert cursor.fetchone()[0] == "761111116"
    assert Empresa.objects.get(rut="76.111.111-6") == empresa_a
    assert Empresa.objects.get(rut="761111116") == empresa_a
    assert str(empresa_a) == "Empresa A de Prueba SpA (76.111.111-6)"


@pytest.mark.django_db
def test_rut_invalido_no_pasa_la_validacion():
    empresa = Empresa(rut="76.111.111-9", razon_social="Con dígito incorrecto")
    with pytest.raises(ValidationError) as error:
        empresa.full_clean()
    assert "rut" in error.value.message_dict


@pytest.mark.django_db
def test_la_base_rechaza_un_rut_sin_normalizar():
    """Aunque se salte la validación de Python, el constraint impide guardar basura."""
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO empresas_empresa (id, rut, razon_social, nombre_fantasia,"
            " contacto_nombre, contacto_email, contacto_telefono, activa, notas_internas,"
            " creado_en, actualizado_en)"
            " VALUES (%s, %s, 'X', '', '', '', '', true, '', now(), now())",
            [uuid.uuid4(), "76.111-6"],
        )


def test_el_rut_es_unico(empresa_a):
    duplicada = Empresa(rut="761111116", razon_social="Otra razón social")
    with pytest.raises(ValidationError):
        duplicada.full_clean()
    with pytest.raises(IntegrityError), transaction.atomic():
        duplicada.save()
