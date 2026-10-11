from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):
    """Extensión `unaccent` de PostgreSQL: el buscador del portal ignora las tildes (CLI-03)."""

    dependencies = [
        ("documentos", "0001_initial"),
    ]

    operations = [
        UnaccentExtension(),
    ]
