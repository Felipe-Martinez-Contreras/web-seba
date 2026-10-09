import pytest
from django.core.exceptions import ValidationError
from django.template import Context, Template

from core import rut
from core.validators import validar_rut


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("12.345.678-5", "123456785"),
        ("12345678-5", "123456785"),
        ("123456785", "123456785"),
        ("  12.345.678-5  ", "123456785"),
        ("6.000.000-k", "6000000K"),
        ("6000000K", "6000000K"),
        ("012.345.678-5", "123456785"),
        ("", ""),
        (None, ""),
    ],
)
def test_normalizar(entrada, esperado):
    assert rut.normalizar(entrada) == esperado


@pytest.mark.parametrize(
    ("cuerpo", "digito"),
    [("12345678", "5"), ("11111111", "1"), ("22222222", "2"), ("6000000", "K"), ("434", "0")],
)
def test_digito_verificador(cuerpo, digito):
    assert rut.digito_verificador(cuerpo) == digito


@pytest.mark.parametrize(
    "valor",
    [
        "12.345.678-5",
        "12345678-5",
        "123456785",
        "11.111.111-1",
        "22.222.222-2",
        "6.000.000-K",
        "6.000.000-k",
        "6000000k",
        "434-0",
    ],
)
def test_rut_valido(valor):
    assert rut.es_valido(valor)
    validar_rut(valor)


@pytest.mark.parametrize(
    "valor",
    [
        "12.345.678-9",  # dígito verificador incorrecto
        "12.345.678-K",
        "6.000.000-0",
        "12.345.678",  # falta el dígito: 1234567-8 no es válido
        "123.456.789-5",  # cuerpo de 9 dígitos
        "12.345.678-5x",
        "abc",
        "K",
        "0",
        "0-0",
        "",
        None,
        "12,345,678-5",
        "１２３４５６７８-5",  # dígitos que no son ASCII
    ],
)
def test_rut_invalido(valor):
    assert not rut.es_valido(valor)
    with pytest.raises(ValidationError):
        validar_rut(valor)


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("123456785", "12.345.678-5"),
        ("12345678-5", "12.345.678-5"),
        ("6000000k", "6.000.000-K"),
        ("4340", "434-0"),
        ("no es rut", "no es rut"),
        ("", ""),
    ],
)
def test_formatear(entrada, esperado):
    assert rut.formatear(entrada) == esperado


def test_filtro_de_plantilla_rut():
    plantilla = Template("{% load formato %}{{ valor|rut }}")
    assert plantilla.render(Context({"valor": "123456785"})) == "12.345.678-5"
