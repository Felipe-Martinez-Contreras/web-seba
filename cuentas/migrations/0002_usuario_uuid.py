import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    """Paso 1 de 3: el campo entra sin restricción para poder poblar las filas existentes."""

    dependencies = [("cuentas", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="uuid",
            field=models.UUIDField(
                default=uuid.uuid4, editable=False, null=True, verbose_name="identificador público"
            ),
        ),
    ]
