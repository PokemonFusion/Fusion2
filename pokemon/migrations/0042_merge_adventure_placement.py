"""Join Adventure participation and canonical placement migration histories."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("pokemon", "0040_adventure_participation"),
        ("pokemon", "0041_placement_integrity_triggers"),
    ]

    operations = []
