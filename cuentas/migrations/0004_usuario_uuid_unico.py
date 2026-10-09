import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    """Paso 3 de 3: con todas las filas pobladas, el campo pasa a ser único y obligatorio."""

    dependencies = [("cuentas", "0003_poblar_uuid")]

    operations = [
        migrations.AlterField(
            model_name="usuario",
            name="uuid",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
                verbose_name="identificador público",
            ),
        ),
    ]
