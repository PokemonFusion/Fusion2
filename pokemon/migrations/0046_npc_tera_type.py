"""Allow authored NPC teams to select a Tera type, including Stellar."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Leave existing NPC teams on the ordinary primary-type fallback."""

    dependencies = [("pokemon", "0045_production_strategy_gym")]
    operations = [
        migrations.AddField(
            model_name="npcpokemontemplate", name="tera_type",
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
