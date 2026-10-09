from django.contrib.auth.base_user import BaseUserManager


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _crear(self, rut, password, **campos):
        if not rut:
            raise ValueError("El RUT de acceso es obligatorio.")
        usuario = self.model(rut=rut, **campos)
        # Con password=None queda una contraseña no utilizable hasta que la cuenta se active.
        usuario.set_password(password)
        usuario.full_clean()
        usuario.save(using=self._db)
        return usuario

    def create_user(self, rut, password=None, **campos):
        """Crea una cuenta del negocio (administrador o cliente), sin privilegios técnicos."""
        if campos.get("is_staff") or campos.get("is_superuser"):
            raise ValueError(
                "Las cuentas del negocio no llevan is_staff ni is_superuser; "
                "use create_superuser para el superusuario técnico."
            )
        campos["is_staff"] = False
        campos["is_superuser"] = False
        return self._crear(rut, password, **campos)

    def create_superuser(self, rut, password=None, **campos):
        """Crea el superusuario técnico que usa el admin de Django para soporte."""
        campos["rol"] = self.model.Rol.ADMINISTRADOR
        campos["empresa"] = None
        campos["is_staff"] = True
        campos["is_superuser"] = True
        return self._crear(rut, password, **campos)
