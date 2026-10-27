"""Persist authored gym definitions and launch version identities."""
from django.db import migrations, models


class Migration(migrations.Migration):
    """Keep existing gyms unmanaged until deliberate content installation."""

    dependencies = [("pokemon", "0054_breeding_integrity")]
    operations = [
        migrations.AddField(model_name="gymleaderprofile", name="content_version", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="gymleaderprofile", name="content_digest", field=models.CharField(blank=True, default="", max_length=64)),
        migrations.AddField(model_name="gymleaderprofile", name="content_definition", field=models.JSONField(blank=True, default=dict)),
    ]
