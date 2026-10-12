import io
from unittest import mock

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import SystemCheckError


def test_preparar_despliegue_migra_crea_la_cache_y_revisa_en_ese_orden():
    with mock.patch("core.management.commands.preparar_despliegue.call_command") as llamar:
        call_command("preparar_despliegue")
    assert [llamada.args[0] for llamada in llamar.call_args_list] == [
        "migrate",
        "createcachetable",
        "check",
    ]
    assert llamar.call_args_list[0].kwargs["interactive"] is False
    assert llamar.call_args_list[2].kwargs["deploy"] is True


CORREO_SMTP = {"default": {"BACKEND": "django.core.mail.backends.smtp.EmailBackend"}}


@pytest.mark.django_db
def test_preparar_despliegue_corre_de_verdad_y_deja_la_cache_utilizable(settings):
    settings.MAILERS = CORREO_SMTP
    salida = io.StringIO()
    call_command("preparar_despliegue", stdout=salida, stderr=salida)
    assert "No migrations to apply." in salida.getvalue()
    cache.set("preparar-despliegue", "ok", 30)
    assert cache.get("preparar-despliegue") == "ok"


@pytest.mark.django_db
def test_preparar_despliegue_termina_con_error_si_check_deploy_encuentra_uno():
    """Así `desplegar.sh` se detiene antes de reiniciar la aplicación. El error es real:
    la configuración de las pruebas usa un correo que no sirve para producción."""
    with pytest.raises(SystemCheckError, match="mail.E001"):
        call_command("preparar_despliegue", stdout=io.StringIO(), stderr=io.StringIO())
