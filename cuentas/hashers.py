from django.contrib.auth.hashers import Argon2PasswordHasher


class Argon2idAcotado(Argon2PasswordHasher):
    """Argon2id con el costo que recomienda OWASP para poca memoria: 19 MiB, 2 pasadas y
    1 hilo. Los valores por omisión de Django reservan unos 100 MiB por cada verificación:
    en la máquina de 1 GB, unos pocos accesos simultáneos agotaban la memoria (DEC-198).

    Conserva el nombre de algoritmo `argon2`: las contraseñas guardadas con el costo
    anterior se siguen verificando y se vuelven a guardar con este en el siguiente acceso.
    """

    time_cost = 2
    memory_cost = 19456
    parallelism = 1
