"""Corte del acceso en la petición siguiente (AUT-11; prueba 5 de la sección 12.2; E6)."""

import pytest
from django.contrib.sessions.models import Session

from conftest import RUT_CLIENTE_A, entrar
from cuentas.backends import BackendRut

pytestmark = pytest.mark.django_db


def test_un_usuario_desactivado_pierde_el_acceso_en_la_peticion_siguiente(client, cliente_a_activo):
    entrar(client, RUT_CLIENTE_A)
    assert client.get("/portal/").status_code == 200
    assert Session.objects.count() == 1

    cliente_a_activo.is_active = False
    cliente_a_activo.save()

    respuesta = client.get("/portal/")
    assert respuesta.status_code == 302
    assert respuesta["Location"] == "/acceso/?next=/portal/"
    # La sesión no queda dormida: se elimina.
    assert Session.objects.count() == 0

    # Reactivar la cuenta no revive la sesión anterior.
    cliente_a_activo.is_active = True
    cliente_a_activo.save()
    assert client.get("/portal/").status_code == 302


def test_desactivar_la_empresa_corta_a_sus_usuarios_y_no_a_los_de_otra(
    client, cliente_a_activo, cliente_b_activo, empresa_a
):
    from django.test import Client

    otro = Client()
    entrar(client, RUT_CLIENTE_A)
    entrar(otro, cliente_b_activo.rut)
    assert client.get("/portal/").status_code == 200

    empresa_a.activa = False
    empresa_a.save()

    assert client.get("/portal/")["Location"] == "/acceso/?next=/portal/"
    assert client.get("/cuenta/").status_code == 302
    assert otro.get("/portal/").status_code == 200
    # Tampoco puede volver a entrar mientras la empresa siga desactivada.
    assert entrar(client, RUT_CLIENTE_A).status_code == 200


def test_un_administrador_desactivado_pierde_el_panel(cliente_http_admin, administrador_activo):
    assert cliente_http_admin.get("/panel/").status_code == 200
    administrador_activo.is_active = False
    administrador_activo.save()
    assert cliente_http_admin.get("/panel/")["Location"] == "/acceso/?next=/panel/"
    assert Session.objects.count() == 0


def test_el_backend_comprueba_la_cuenta_y_la_empresa_en_una_sola_consulta(
    cliente_a_activo, empresa_a, django_assert_num_queries
):
    backend = BackendRut()
    with django_assert_num_queries(1):
        usuario = backend.get_user(cliente_a_activo.pk)
        assert usuario.empresa.activa is True
    empresa_a.activa = False
    empresa_a.save()
    assert backend.get_user(cliente_a_activo.pk) is None
    assert backend.get_user(999_999) is None
