"""Datos de prueba compartidos: dos empresas (A y B), un cliente por empresa y un administrador."""

import pytest

from cuentas.models import Usuario
from empresas.models import Empresa


@pytest.fixture
def empresa_a(db):
    return Empresa.objects.create(rut="76.111.111-6", razon_social="Empresa A de Prueba SpA")


@pytest.fixture
def empresa_b(db):
    return Empresa.objects.create(rut="76.222.222-1", razon_social="Empresa B de Prueba Ltda.")


@pytest.fixture
def cliente_a(empresa_a):
    return Usuario.objects.create_user(
        "11.111.111-1", nombre="Cliente de A", rol=Usuario.Rol.CLIENTE, empresa=empresa_a
    )


@pytest.fixture
def cliente_b(empresa_b):
    return Usuario.objects.create_user(
        "22.222.222-2", nombre="Cliente de B", rol=Usuario.Rol.CLIENTE, empresa=empresa_b
    )


@pytest.fixture
def administrador(db):
    return Usuario.objects.create_user(
        "12.345.678-5",
        nombre="Administradora de Prueba",
        email="admin@ejemplo.test",
        rol=Usuario.Rol.ADMINISTRADOR,
    )
