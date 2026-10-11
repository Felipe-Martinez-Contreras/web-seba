from django.db import migrations


def crear_registro(apps, schema_editor):
    """Crea, vacío, el registro único de los datos del negocio: todo queda pendiente hasta
    que el responsable lo complete desde el panel."""
    apps.get_model("sitio", "DatosNegocio").objects.get_or_create(pk=1)


class Migration(migrations.Migration):
    dependencies = [("sitio", "0001_initial")]

    operations = [migrations.RunPython(crear_registro, migrations.RunPython.noop)]
