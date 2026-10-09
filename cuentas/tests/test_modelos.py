import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError

from cuentas.models import Usuario
from empresas.models import Empresa


def test_el_modelo_de_usuario_es_el_personalizado():
    assert get_user_model() is Usuario
    assert Usuario.USERNAME_FIELD == "rut"
    assert Usuario._meta.get_field("rut").unique is True


def test_create_user_sin_contrasena_deja_una_contrasena_no_utilizable(cliente_a):
    cliente_a.refresh_from_db()
    assert cliente_a.has_usable_password() is False
    assert cliente_a.check_password("") is False
    assert cliente_a.check_password("None") is False


def test_create_user_con_contrasena_la_guarda_con_argon2(empresa_a):
    usuario = Usuario.objects.create_user(
        "11.111.111-1",
        password="una frase larga y segura",
        nombre="Con Clave",
        rol=Usuario.Rol.CLIENTE,
        empresa=empresa_a,
    )
    usuario.refresh_from_db()
    assert usuario.password.startswith("argon2$argon2id$")
    assert usuario.check_password("una frase larga y segura") is True


def test_el_rut_se_normaliza_al_crear_y_se_busca_en_cualquier_formato(cliente_a):
    cliente_a.refresh_from_db()
    assert cliente_a.rut == "111111111"
    assert Usuario.objects.get(rut="11.111.111-1") == cliente_a
    assert Usuario.objects.get_by_natural_key("11111111-1") == cliente_a
    assert str(cliente_a) == "Cliente de A (11.111.111-1)"


def test_el_rut_es_unico_aunque_cambie_el_formato(cliente_a, empresa_b):
    with pytest.raises(ValidationError):
        Usuario.objects.create_user(
            "111111111", nombre="Duplicado", rol=Usuario.Rol.CLIENTE, empresa=empresa_b
        )
    duplicado = Usuario(
        rut="11111111-1", nombre="Duplicado", rol=Usuario.Rol.CLIENTE, empresa=empresa_b
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        duplicado.save()


@pytest.mark.django_db
def test_create_user_rechaza_un_rut_invalido_o_vacio():
    with pytest.raises(ValidationError):
        Usuario.objects.create_user(
            "12.345.678-9",
            nombre="Dígito incorrecto",
            email="a@ejemplo.test",
            rol=Usuario.Rol.ADMINISTRADOR,
        )
    with pytest.raises(ValueError, match="RUT"):
        Usuario.objects.create_user("", nombre="Sin RUT", rol=Usuario.Rol.ADMINISTRADOR)
    assert Usuario.objects.count() == 0


# --- Regla "cliente con empresa, administrador sin empresa", en la base de datos ---


@pytest.mark.django_db
def test_la_base_rechaza_un_cliente_sin_empresa():
    usuario = Usuario(rut="11.111.111-1", nombre="Cliente huérfano", rol=Usuario.Rol.CLIENTE)
    # save() no ejecuta validaciones de Python: el rechazo viene del CheckConstraint.
    with (
        pytest.raises(IntegrityError, match="usuario_rol_coherente_con_empresa"),
        transaction.atomic(),
    ):
        usuario.save()
    assert Usuario.objects.count() == 0


def test_la_base_rechaza_un_administrador_con_empresa(empresa_a):
    usuario = Usuario(
        rut="12.345.678-5",
        nombre="Administrador con empresa",
        email="a@ejemplo.test",
        rol=Usuario.Rol.ADMINISTRADOR,
        empresa=empresa_a,
    )
    with (
        pytest.raises(IntegrityError, match="usuario_rol_coherente_con_empresa"),
        transaction.atomic(),
    ):
        usuario.save()
    assert Usuario.objects.count() == 0


def test_la_base_rechaza_cambiar_el_rol_dejando_la_cuenta_incoherente(cliente_a, administrador):
    with pytest.raises(IntegrityError), transaction.atomic():
        Usuario.objects.filter(pk=cliente_a.pk).update(rol=Usuario.Rol.ADMINISTRADOR)
    with pytest.raises(IntegrityError), transaction.atomic():
        Usuario.objects.filter(pk=administrador.pk).update(rol=Usuario.Rol.CLIENTE)
    with pytest.raises(IntegrityError), transaction.atomic():
        Usuario.objects.filter(pk=cliente_a.pk).update(empresa=None)


def test_la_base_rechaza_un_rol_desconocido(empresa_a):
    usuario = Usuario(rut="11.111.111-1", nombre="Rol raro", rol="auditor", empresa=empresa_a)
    with pytest.raises(IntegrityError), transaction.atomic():
        usuario.save()


def test_create_user_valida_la_regla_antes_de_llegar_a_la_base(empresa_a):
    with pytest.raises(ValidationError):
        Usuario.objects.create_user("11.111.111-1", nombre="Sin empresa", rol=Usuario.Rol.CLIENTE)
    with pytest.raises(ValidationError):
        Usuario.objects.create_user(
            "12.345.678-5",
            nombre="Con empresa",
            email="a@ejemplo.test",
            rol=Usuario.Rol.ADMINISTRADOR,
            empresa=empresa_a,
        )
    assert Usuario.objects.count() == 0


@pytest.mark.django_db
def test_el_administrador_necesita_email():
    with pytest.raises(ValidationError) as error:
        Usuario.objects.create_user(
            "12.345.678-5", nombre="Sin email", rol=Usuario.Rol.ADMINISTRADOR
        )
    assert "email" in error.value.message_dict


def test_el_cliente_puede_no_tener_email(cliente_a):
    assert cliente_a.email == ""


# --- is_staff e is_superuser: solo para el superusuario técnico ---


def test_las_cuentas_del_negocio_no_tienen_privilegios_tecnicos(cliente_a, administrador):
    for usuario in (cliente_a, administrador):
        usuario.refresh_from_db()
        assert usuario.is_staff is False
        assert usuario.is_superuser is False
    assert administrador.es_administrador and not administrador.es_cliente
    assert cliente_a.es_cliente and not cliente_a.es_administrador


@pytest.mark.django_db
@pytest.mark.parametrize("privilegio", ["is_staff", "is_superuser"])
def test_create_user_no_admite_privilegios_tecnicos(privilegio):
    with pytest.raises(ValueError, match="create_superuser"):
        Usuario.objects.create_user(
            "12.345.678-5",
            nombre="Administradora",
            email="a@ejemplo.test",
            rol=Usuario.Rol.ADMINISTRADOR,
            **{privilegio: True},
        )
    assert Usuario.objects.count() == 0


@pytest.mark.parametrize("privilegio", ["is_staff", "is_superuser"])
def test_la_base_rechaza_un_cliente_con_privilegios_tecnicos(cliente_a, privilegio):
    with (
        pytest.raises(IntegrityError, match="usuario_cliente_sin_privilegios_tecnicos"),
        transaction.atomic(),
    ):
        Usuario.objects.filter(pk=cliente_a.pk).update(**{privilegio: True})


@pytest.mark.django_db
def test_create_superuser_crea_el_superusuario_tecnico():
    superusuario = Usuario.objects.create_superuser(
        "12.345.678-5",
        password="una frase larga y segura",
        nombre="Soporte Técnico",
        email="soporte@ejemplo.test",
    )
    superusuario.refresh_from_db()
    assert superusuario.is_staff is True
    assert superusuario.is_superuser is True
    assert superusuario.rol == Usuario.Rol.ADMINISTRADOR
    assert superusuario.empresa is None


# --- Usuario → Empresa con PROTECT ---


def test_borrar_una_empresa_con_usuarios_no_borra_nada(cliente_a, empresa_a):
    with pytest.raises(ProtectedError):
        empresa_a.delete()
    with pytest.raises(ProtectedError):
        Empresa.objects.filter(pk=empresa_a.pk).delete()
    assert Empresa.objects.filter(pk=empresa_a.pk).exists()
    assert Usuario.objects.filter(pk=cliente_a.pk).exists()


def test_la_base_tambien_impide_borrar_una_empresa_con_usuarios(cliente_a, empresa_a):
    """Con SQL directo, sin pasar por Django, la clave foránea no borra en cascada."""
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
        # Django crea las claves foráneas diferidas; aquí se comprueban de inmediato.
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        cursor.execute("DELETE FROM empresas_empresa WHERE id = %s", [empresa_a.pk])
    assert Usuario.objects.filter(pk=cliente_a.pk).exists()


def test_cada_empresa_ve_solo_sus_usuarios(cliente_a, cliente_b, empresa_a, empresa_b):
    assert list(empresa_a.usuarios.all()) == [cliente_a]
    assert list(empresa_b.usuarios.all()) == [cliente_b]


def test_cada_usuario_tiene_un_uuid_unico_para_las_url(cliente_a, cliente_b):
    assert cliente_a.uuid != cliente_b.uuid
    assert Usuario._meta.get_field("uuid").unique is True
    assert Usuario._meta.get_field("uuid").editable is False
    # La clave primaria sigue siendo el ID entero, de uso interno.
    assert Usuario._meta.pk.name == "id"
