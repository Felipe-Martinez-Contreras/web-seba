import uuid

from django.db import migrations


def poblar(apps, schema_editor):
    """Paso 2 de 3: cada fila existente recibe su propio UUID."""
    Usuario = apps.get_model("cuentas", "Usuario")
    for usuario in Usuario.objects.all():
        usuario.uuid = uuid.uuid4()
        usuario.save(update_fields=["uuid"])


class Migration(migrations.Migration):
    dependencies = [("cuentas", "0002_usuario_uuid")]

    operations = [migrations.RunPython(poblar, migrations.RunPython.noop)]
