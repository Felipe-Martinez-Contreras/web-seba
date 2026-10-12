from django.conf import settings
from django.contrib.auth.hashers import (
    Argon2PasswordHasher,
    check_password,
    get_hasher,
    identify_hasher,
    make_password,
)

CLAVE = "caballo-bateria-grapa-2026"


def test_el_costo_de_argon2_cabe_en_la_memoria_del_servidor():
    """DEC-198: 19 MiB, 2 pasadas y 1 hilo, el mínimo que recomienda OWASP para Argon2id.
    Con los 100 MiB por omisión, cuatro accesos a la vez pedían casi todo el contenedor."""
    hasher = get_hasher()
    assert settings.PASSWORD_HASHERS == ["cuentas.hashers.Argon2idAcotado"]
    assert (hasher.memory_cost, hasher.time_cost, hasher.parallelism) == (19456, 2, 1)
    assert make_password(CLAVE).startswith("argon2$argon2id$v=19$m=19456,t=2,p=1$")


def test_una_contrasena_guardada_con_el_costo_anterior_sirve_y_se_actualiza_al_entrar():
    antigua = Argon2PasswordHasher().encode(CLAVE, Argon2PasswordHasher().salt())
    assert "$m=102400,t=2,p=8$" in antigua
    assert identify_hasher(antigua).algorithm == "argon2"

    guardadas = []
    assert check_password(CLAVE, antigua, setter=guardadas.append)
    assert guardadas == [CLAVE]
    assert not check_password("otra-clave-distinta-2026", antigua, setter=guardadas.append)
    assert guardadas == [CLAVE]

    nueva = make_password(CLAVE)
    assert check_password(CLAVE, nueva, setter=guardadas.append)
    assert guardadas == [CLAVE]
